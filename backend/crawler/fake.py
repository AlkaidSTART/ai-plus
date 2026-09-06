"""Local demo Amazon data provider (deterministic, clearly labeled demo data).

Used only when no real gateway is configured (dev/demo). Not used by CI
assertions as "real" data — it produces the same deterministic reviews as the
Step 2 providers.
"""

from crawler.base import AmazonDataProvider, AmazonFetchResult, ProductMetadata
from services.providers import DeterministicReviewProvider


class FakeAmazonDataProvider:
    def __init__(self) -> None:
        self._inner = DeterministicReviewProvider()

    async def fetch(
        self, asin: str, marketplace: str, window_months: int, max_reviews: int
    ) -> AmazonFetchResult:
        reviews = await self._inner.fetch(asin, marketplace, window_months, max_reviews)
        metadata = ProductMetadata(
            asin=asin,
            title=f"[Demo] Product {asin}",
            marketplace=marketplace,
            category="Home & Kitchen",
            current_price=29.99,
            main_image_url=None,
            length_cm=30,
            width_cm=20,
            height_cm=12,
            weight_kg=1.2,
        )
        return AmazonFetchResult(metadata=metadata, reviews=reviews)
