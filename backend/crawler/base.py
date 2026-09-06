"""Amazon data provider abstraction.

The concrete upstream (which retail data gateway to call) is a deployment
decision — it must be configurable, never hard-coded. `UpstreamError` is the
single failure type the workflow understands and maps to error code 50201.
"""

from dataclasses import dataclass, field
from typing import Any, Protocol

from agents.state import ReviewItem


class UpstreamError(Exception):
    """Raised when the upstream data source fails after retries."""


@dataclass
class ProductMetadata:
    asin: str
    title: str
    platform: str = "amazon"
    marketplace: str = "US"
    category: str | None = None
    current_price: float | None = None
    currency: str = "USD"
    main_image_url: str | None = None
    length_cm: float | None = None
    width_cm: float | None = None
    height_cm: float | None = None
    weight_kg: float | None = None
    bsr: int | None = None
    bsr_category: str | None = None


@dataclass
class AmazonFetchResult:
    metadata: ProductMetadata
    reviews: list[ReviewItem] = field(default_factory=list)


class AmazonDataProvider(Protocol):
    async def fetch(
        self, asin: str, marketplace: str, window_months: int, max_reviews: int
    ) -> AmazonFetchResult: ...


class AmazonDataProviderFactory(Protocol):
    def for_marketplace(self, marketplace: str) -> AmazonDataProvider: ...


def normalize_review(raw: dict[str, Any], asin: str) -> ReviewItem:
    return ReviewItem(
        review_id=str(raw["review_id"]),
        asin=asin,
        rating=float(raw.get("rating") or 0),
        review_date=str(raw.get("review_date") or ""),
        language=str(raw.get("language") or "en"),
        title=str(raw.get("title") or ""),
        content=str(raw.get("content") or ""),
        translated_content=raw.get("translated_content"),
        verified_purchase=bool(raw.get("verified_purchase", False)),
        helpful_votes=int(raw.get("helpful_votes") or 0),
        image_urls=[str(u) for u in raw.get("image_urls", [])],
    )


# 无意义极短评价过滤（PRD P0-02: "ok"、"fast shipping" 等）
MEANINGLESS_REVIEWS = {
    "ok", "good", "great", "nice", "fast", "fast shipping", "good product",
    "fine", "works", "perfect", "excellent", "wow", "good quality",
}
MIN_REVIEW_CHARS = 12


def is_meaningless(content: str) -> bool:
    text = content.strip().lower()
    if len(text) < MIN_REVIEW_CHARS:
        return True
    return text in MEANINGLESS_REVIEWS
