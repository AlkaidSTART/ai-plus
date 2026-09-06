"""Dashboard & financial API schemas (docs/api.md §5, §9)."""

from typing import Any

from pydantic import BaseModel, Field

from api.schemas.common import PageData


class DashboardOverview(BaseModel):
    monitored_product_count: int = 0
    running_task_count: int = 0
    pain_point_cluster_count: int = 0
    fba_saving_pool_usd: float = 0.0
    veto_triggered_count: int = 0
    avg_rating: float | None = None
    negative_review_rate: float | None = None


class RecommendationItem(BaseModel):
    task_id: str
    product_id: str | None = None
    asin: str
    title: str | None = None
    main_image_url: str | None = None
    estimated_roi: float | None = None
    return_rate_reduction: float | None = None
    veto_status: str = "PENDING"
    finished_at: str | None = None


class RecommendationPage(PageData[RecommendationItem]):
    pass


class SimulateRequest(BaseModel):
    model_config = {"extra": "allow"}

    mold_cost_usd: float = 0
    moq: int = Field(default=0, ge=0)
    current_gross_margin: float = Field(default=0, ge=0, le=1)
    expected_price_usd: float = 0
    unit_cost_increase_usd: float = 0
    expected_payback_months: float | None = None
    sea_freight_usd_per_cbm: float | None = None
    package_size_old_cm: list[int] | None = None
    package_size_new_cm: list[int] | None = None
    expected_return_rate_reduction: float = Field(default=0, ge=0, le=1)
    product_lifecycle_days: int = 365


class SimulateResult(BaseModel):
    model_config = {"extra": "allow"}


class FinancialResultOut(BaseModel):
    task_id: str
    veto_status: str
    checked_proposals: int
    vetoed_proposal_ids: list[str]
    veto_reasons: list[str]
    fallback_applied: bool
    retry_count: int
    financial_constraint: dict[str, Any] = Field(default_factory=dict)
