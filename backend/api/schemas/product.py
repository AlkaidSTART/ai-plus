"""Product / review API schemas (docs/api.md §6, §7.1)."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel

from api.schemas.common import PageData


class ProductOut(BaseModel):
    product_id: str
    asin: str
    platform: str
    marketplace: str
    title: str
    category: str | None = None
    current_price: float | None = None
    currency: str = "USD"
    main_image_url: str | None = None
    review_count: int | None = None
    avg_rating: float | None = None
    bsr: int | None = None
    updated_at: datetime | None = None


class ProductDetailOut(ProductOut):
    length_cm: float | None = None
    width_cm: float | None = None
    height_cm: float | None = None
    weight_kg: float | None = None
    bsr_category: str | None = None
    created_at: datetime | None = None


class ReviewOut(BaseModel):
    review_id: str
    rating: float
    review_date: str | None = None
    language: str = "en"
    title: str | None = None
    content: str
    translated_content: str | None = None
    verified_purchase: bool = False
    helpful_votes: int = 0
    image_urls: list[str] = []
    cluster_ids: list[str] = []


class ProductPage(PageData[ProductOut]):
    pass


class ReviewPage(PageData[ReviewOut]):
    pass


class PriceHistoryPoint(BaseModel):
    ts: datetime
    price: float | None = None
    bsr: int | None = None
    buy_box_price: float | None = None
    has_coupon: bool = False
