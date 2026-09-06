"""Repositories for products and reviews (incl. pgvector writes)."""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from crawler.base import ProductMetadata
from db.models import Product, Review, ReviewImage

CACHE_TTL_HOURS = 24


class ProductRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_or_create(
        self, metadata: ProductMetadata
    ) -> tuple[Product, bool]:
        row = await self.session.scalar(
            select(Product).where(
                Product.asin == metadata.asin,
                Product.platform == metadata.platform,
                Product.marketplace == metadata.marketplace,
            )
        )
        if row is not None:
            return row, False
        row = Product(
            asin=metadata.asin,
            platform=metadata.platform,
            marketplace=metadata.marketplace,
            title=metadata.title,
            category=metadata.category,
            current_price=metadata.current_price,
            currency=metadata.currency,
            main_image_url=metadata.main_image_url,
            length_cm=metadata.length_cm,
            width_cm=metadata.width_cm,
            height_cm=metadata.height_cm,
            weight_kg=metadata.weight_kg,
            bsr=metadata.bsr,
            bsr_category=metadata.bsr_category,
        )
        self.session.add(row)
        await self.session.flush()
        return row, True

    async def get(self, product_id: str) -> Product | None:
        try:
            pid = uuid.UUID(product_id)
        except ValueError:
            return None
        return await self.session.scalar(select(Product).where(Product.id == pid))


class ReviewRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert(
        self,
        product: Product,
        reviews: list[dict[str, Any]],
        embeddings: list[list[float]] | None = None,
    ) -> int:
        """Idempotent upsert keyed by (product_id, external_review_id)."""
        count = 0
        for i, review in enumerate(reviews):
            external_id = str(review["review_id"])
            existing = await self.session.scalar(
                select(Review).where(
                    Review.product_id == product.id,
                    Review.external_review_id == external_id,
                )
            )
            values = dict(
                rating=review["rating"],
                review_date=review.get("review_date"),
                original_language=review.get("language", "en"),
                title=review.get("title"),
                content=review["content"],
                translated_content=review.get("translated_content"),
                verified_purchase=review.get("verified_purchase", False),
                helpful_votes=review.get("helpful_votes", 0),
            )
            if embeddings is not None:
                values["embedding"] = embeddings[i]
            if existing is not None:
                for key, value in values.items():
                    setattr(existing, key, value)
            else:
                self.session.add(Review(product_id=product.id, external_review_id=external_id, **values))
            count += 1
        await self.session.flush()
        return count

    async def add_image(
        self, review: Review, storage_url: str, defect_type: str | None = None,
        vlm_analysis: dict | None = None,
    ) -> ReviewImage:
        image = ReviewImage(
            review_id=review.id,
            storage_url=storage_url,
            defect_type=defect_type,
            vlm_analysis=vlm_analysis,
        )
        self.session.add(image)
        await self.session.flush()
        return image

    async def reviews_fetched_since(self, product: Product, hours: float) -> int:
        """Number of reviews stored for the product; freshness via cache window."""
        threshold = datetime.now(UTC) - timedelta(hours=hours)
        count = await self.session.scalar(
            select(func.count()).select_from(Review).where(
                Review.product_id == product.id,
                Review.created_at >= threshold,
            )
        )
        return int(count or 0)

    async def list_for_product(
        self,
        product_id: uuid.UUID,
        rating_min: float | None = None,
        rating_max: float | None = None,
        language: str | None = None,
        verified_only: bool | None = None,
        keyword: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Review], int]:
        stmt = select(Review).where(Review.product_id == product_id)
        if rating_min is not None:
            stmt = stmt.where(Review.rating >= rating_min)
        if rating_max is not None:
            stmt = stmt.where(Review.rating <= rating_max)
        if language is not None:
            stmt = stmt.where(Review.original_language == language)
        if verified_only:
            stmt = stmt.where(Review.verified_purchase.is_(True))
        if keyword:
            stmt = stmt.where(Review.content.ilike(f"%{keyword}%"))
        total = await self.session.scalar(select(func.count()).select_from(stmt.subquery()))
        rows = (
            await self.session.scalars(
                stmt.order_by(Review.review_date.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        ).all()
        return list(rows), int(total or 0)
