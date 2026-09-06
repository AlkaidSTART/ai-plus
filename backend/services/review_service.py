"""Review ingestion service: ASIN → metadata + reviews → cleaning → DB.

Caching: the same ASIN + marketplace reuses fetched review data within the
cache window (docs/api.md §1.4), so repeated tasks do not re-scrape.
"""

import logging
import time
from dataclasses import dataclass

from sqlalchemy import select

from crawler.base import (
    AmazonDataProvider,
    AmazonFetchResult,
    is_meaningless,
)
from db.models import Review
from db.repositories.review_repository import ProductRepository, ReviewRepository
from db.session import get_sessionmaker

logger = logging.getLogger(__name__)


@dataclass
class ReviewFetchOutcome:
    reviews: list[dict]
    metadata: AmazonFetchResult | None
    cache_hit: bool
    filtered_count: int


class ReviewService:
    def __init__(
        self,
        provider: AmazonDataProvider,
        cache_ttl_hours: float = 24.0,
    ) -> None:
        self.provider = provider
        self.cache_ttl_hours = cache_ttl_hours
        self._cache: dict[tuple[str, str], tuple[float, AmazonFetchResult]] = {}

    async def fetch_for_task(
        self,
        asin: str,
        marketplace: str,
        window_months: int,
        max_reviews: int,
        persist: bool = True,
    ) -> ReviewFetchOutcome:
        key = (asin, marketplace)
        cached = self._cache.get(key)
        if cached and time.monotonic() - cached[0] < self.cache_ttl_hours * 3600:
            result = cached[1]
            cache_hit = True
        else:
            result = await self.provider.fetch(asin, marketplace, window_months, max_reviews)
            self._cache[key] = (time.monotonic(), result)
            cache_hit = False

        cleaned = [r for r in result.reviews if not is_meaningless(r["content"])]
        filtered_count = len(result.reviews) - len(cleaned)
        if filtered_count:
            logger.info("filtered %d meaningless reviews for %s", filtered_count, asin)

        if persist:
            try:
                await self._persist(result, cleaned)
            except Exception:  # noqa: BLE001 - persistence must not kill the workflow
                logger.exception("review persistence failed for %s", asin)

        return ReviewFetchOutcome(
            reviews=cleaned, metadata=result, cache_hit=cache_hit, filtered_count=filtered_count
        )

    async def _persist(self, result: AmazonFetchResult, cleaned: list[dict]) -> None:
        async with get_sessionmaker()() as session:
            product_repo = ProductRepository(session)
            review_repo = ReviewRepository(session)
            product, _ = await product_repo.get_or_create(result.metadata)
            db_reviews = [
                {
                    "review_id": r["review_id"],
                    "rating": r["rating"],
                    "review_date": r["review_date"],
                    "language": r["language"],
                    "title": r["title"],
                    "content": r["content"],
                    "translated_content": r["translated_content"],
                    "verified_purchase": r["verified_purchase"],
                    "helpful_votes": r["helpful_votes"],
                }
                for r in cleaned
            ]
            await review_repo.upsert(product, db_reviews)
            kept_ids = {r["review_id"] for r in cleaned}
            for r in result.reviews:
                if r["review_id"] not in kept_ids or not r["image_urls"]:
                    continue
                review_row = await session.scalar(
                    select(Review).where(
                        Review.product_id == product.id,
                        Review.external_review_id == r["review_id"],
                    )
                )
                if review_row is not None:
                    for url in r["image_urls"]:
                        await review_repo.add_image(review_row, url)
            await session.commit()
