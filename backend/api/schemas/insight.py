"""Insight task API schemas (docs/api.md §4)."""

from typing import Any

from pydantic import BaseModel, Field

from api.schemas.common import Envelope, PageData
from runtime.task_store import TaskOptions, TaskRecord, TaskStatus

TASK_DETAIL_KEYS = (
    "task_id",
    "asin",
    "product_id",
    "platform",
    "marketplace",
    "status",
    "current_node",
    "progress",
    "retry_count",
    "financial_constraint",
    "summary",
    "error_message",
    "created_at",
    "started_at",
    "finished_at",
)


class FinancialConstraintIn(BaseModel):
    model_config = {"extra": "allow"}

    mold_cost_usd: float = 0
    moq: int = 0
    current_gross_margin: float = 0
    expected_price_usd: float = 0
    unit_cost_increase_usd: float = 0
    expected_payback_months: float | None = None
    sea_freight_usd_per_cbm: float | None = None


class CreateTasksRequest(BaseModel):
    asins: list[str] = Field(default_factory=list)
    amazon_url: str | None = None
    platform: str = "amazon"
    marketplace: str = "US"
    review_window_months: int = Field(default=6, ge=1, le=24)
    max_reviews: int = Field(default=500, ge=1, le=2000)
    financial_constraint: FinancialConstraintIn = Field(default_factory=FinancialConstraintIn)
    options: TaskOptions = Field(default_factory=TaskOptions)


class TaskCreatedItem(BaseModel):
    task_id: str
    asin: str
    product_id: str | None = None
    status: str
    cache_hit: bool = False
    estimated_seconds: int = 45
    created_at: str | None = None


class TaskListData(BaseModel):
    tasks: list[TaskCreatedItem]


class TaskSummaryOut(BaseModel):
    review_count: int | None = None
    cluster_count: int | None = None
    proposal_count: int | None = None
    veto_status: str = "PENDING"
    backtest_score: float | None = None
    avg_rating: float | None = None
    negative_review_rate: float | None = None


class TaskDetail(BaseModel):
    task_id: str
    asin: str
    product_id: str | None = None
    platform: str = "amazon"
    marketplace: str = "US"
    status: str
    current_node: str | None = None
    progress: int = 0
    retry_count: int = 0
    financial_constraint: dict[str, Any] = Field(default_factory=dict)
    summary: TaskSummaryOut = Field(default_factory=TaskSummaryOut)
    error_message: str | None = None
    created_at: str | None = None
    started_at: str | None = None
    finished_at: str | None = None


def to_task_detail(record: TaskRecord) -> TaskDetail:
    data = record.model_dump()
    return TaskDetail(**{key: data[key] for key in TASK_DETAIL_KEYS})


class TaskDetailData(Envelope[TaskDetail]):
    pass


class TaskPageData(PageData[TaskDetail]):
    pass
