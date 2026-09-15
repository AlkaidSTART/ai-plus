"""Pydantic request and response models for the version 1 API."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated, Any, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer, field_validator


def serialize_utc_datetime(value: datetime) -> str:
    """Serialize a datetime as an ISO 8601 UTC string ending in ``Z``."""

    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


UtcDateTime = Annotated[
    datetime,
    PlainSerializer(serialize_utc_datetime, return_type=str, when_used="json"),
]


class TaskStatus(StrEnum):
    """Lifecycle state shared by tasks and task items."""

    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELED = "CANCELED"


class DataQuality(StrEnum):
    """Report data quality."""

    SUFFICIENT = "SUFFICIENT"
    PARTIAL = "PARTIAL"
    NO_DATA = "NO_DATA"


class FinancialState(StrEnum):
    """Deterministic financial evaluation state."""

    NOT_EVALUATED = "NOT_EVALUATED"
    PASSED = "PASSED"
    VETOED = "VETOED"


class NodeStatus(StrEnum):
    """Execution state for one reported task node."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    SKIPPED = "SKIPPED"
    FAILED = "FAILED"
    CANCELED = "CANCELED"


class EvidenceSourceType(StrEnum):
    """Supported text evidence source types for P0."""

    REVIEW_TEXT = "REVIEW_TEXT"
    CLEANED_FRAGMENT = "CLEANED_FRAGMENT"
    METADATA = "METADATA"


class StrictModel(BaseModel):
    """Base model that rejects undeclared request fields."""

    model_config = ConfigDict(extra="forbid")


class TaskWindow(StrictModel):
    """Normalized task analysis window."""

    preset: Literal["1m", "3m", "6m"]


class TaskCreateRequest(StrictModel):
    """Request body for creating a task batch."""

    asins: list[str] = Field(min_length=1, max_length=10)
    platform: Literal["amazon"]
    marketplace: Literal["US"]
    window: TaskWindow

    @field_validator("asins", mode="before")
    @classmethod
    def normalize_asins(cls, asins: Any) -> Any:
        """Uppercase and deduplicate ASINs while preserving first-use order."""

        if not isinstance(asins, list):
            return asins
        if not all(isinstance(asin, str) for asin in asins):
            return asins
        normalized = list(dict.fromkeys(asin.upper() for asin in asins))
        invalid = [
            asin
            for asin in normalized
            if len(asin) != 10 or not asin.isascii() or not asin.isalnum()
        ]
        if invalid:
            raise ValueError("ASIN must match ^[A-Z0-9]{10}$")
        return normalized


class RetryTaskRequest(StrictModel):
    """Request body for retrying failed task items."""

    item_ids: list[str] = Field(min_length=1)

    @field_validator("item_ids")
    @classmethod
    def normalize_item_ids(cls, item_ids: list[str]) -> list[str]:
        """Deduplicate item IDs while preserving first-use order."""

        return list(dict.fromkeys(item_ids))


class TaskCreatedItem(StrictModel):
    """Item summary returned when a task is accepted."""

    item_id: str
    asin: str
    status: TaskStatus


class TaskCreatedResponse(StrictModel):
    """Response returned for task creation and retry operations."""

    task_id: str
    status: TaskStatus
    reused: bool
    parent_task_id: str | None
    created_at: UtcDateTime
    items: list[TaskCreatedItem]


class TaskListItem(StrictModel):
    """Task summary used by cursor-paginated task lists."""

    task_id: str
    status: TaskStatus
    platform: str
    marketplace: str
    window: TaskWindow
    created_at: UtcDateTime
    updated_at: UtcDateTime
    total_items: int
    completed_items: int
    failed_items: int
    canceled_items: int
    last_event_id: str | None


class TaskError(StrictModel):
    """Structured task or node error."""

    code: str
    message: str
    retryable: bool


class SampleMetrics(StrictModel):
    """Actual sample statistics associated with an item or report."""

    raw_review_count: int = Field(ge=0)
    valid_review_count: int = Field(ge=0)
    excluded_review_count: int = Field(ge=0)
    average_rating: float | None
    negative_review_ratio: float | None = Field(ge=0, le=1)
    pain_point_count_with_evidence: int = Field(ge=0)
    window: dict[str, Any]
    methodology: str
    missing_reasons: list[str]


class NodeProgress(StrictModel):
    """One real execution record for a task item node."""

    node_id: str
    node_name: str
    status: NodeStatus
    started_at: UtcDateTime | None
    finished_at: UtcDateTime | None
    duration_ms: int | None
    skip_reason: str | None
    error: TaskError | None


class TaskItemSnapshot(StrictModel):
    """Point-in-time state for one task item."""

    item_id: str
    asin: str
    status: TaskStatus
    current_node: str | None
    attempt: int
    data_quality: DataQuality | None
    sample_metrics: SampleMetrics | None
    nodes: list[NodeProgress]
    error: TaskError | None
    report_available: bool


class TaskProgress(StrictModel):
    """Batch-level aggregate progress."""

    total_items: int
    finished_items: int


class TaskSnapshot(TaskListItem):
    """Recoverable task state including item details."""

    parent_task_id: str | None
    cancel_requested_at: UtcDateTime | None
    finished_at: UtcDateTime | None
    items: list[TaskItemSnapshot]
    progress: TaskProgress


class ReportPainPoint(StrictModel):
    """Evidence-backed pain point in a generated report."""

    pain_point_id: str
    label: str
    actual_frequency: int = Field(ge=0)
    frequency_methodology: str
    severity_score: int = Field(ge=1, le=5)
    severity_rationale: str
    severity_level: Literal["CRITICAL", "MODERATE", "MINOR"]
    summary: str
    evidence_refs: list[str] = Field(min_length=1)
    typical_evidence_refs: list[str] = Field(min_length=1)


class ReportProposal(StrictModel):
    """Evidence-backed recommendation in a generated report."""

    proposal_id: str
    column: Literal["PRODUCT_OPTIMIZATION", "PACKAGING_FULFILLMENT_OPTIMIZATION"]
    title: str
    change_description: str
    pain_point_ids: list[str] = Field(min_length=1)
    snapshot_ref: str
    evidence_refs: list[str] = Field(min_length=1)


class ReportWarning(StrictModel):
    """Warning attached to a report."""

    code: str
    message: str
    related_item_id: str | None = None
    evidence_refs: list[str] | None = None


class ReportResponse(StrictModel):
    """Generated diagnosis report response."""

    report_id: str
    task_id: str
    item_id: str
    asin: str
    data_quality: DataQuality
    sample_metrics: SampleMetrics
    generated_at: UtcDateTime
    financial_state: FinancialState
    pain_points: list[ReportPainPoint]
    proposals: list[ReportProposal]
    warnings: list[ReportWarning]
    model_metadata: dict[str, Any]


class EvidenceResponse(StrictModel):
    """Public representation of one evidence record."""

    evidence_id: str
    source_type: EvidenceSourceType
    source_ref: str
    excerpt: str
    source_url: str | None
    published_at: UtcDateTime | None
    metadata: dict[str, Any]
    provenance: dict[str, Any]


class FinancialEvaluateRequest(StrictModel):
    """Input parameters for deterministic financial risk and veto evaluation."""

    mold_cost: float | None = Field(default=None, ge=0)
    sample_cost: float | None = Field(default=None, ge=0)
    moq: int | None = Field(default=None, ge=1)
    unit_product_cost: float | None = Field(default=None, ge=0)
    expected_sales_price: float | None = Field(default=None, ge=0)
    shipping_cost_per_unit: float | None = Field(default=None, ge=0)
    monthly_estimated_sales: int | None = Field(default=None, ge=1)
    target_payback_months: int = Field(default=6, ge=1, le=60)
    category_half_life_months: int = Field(default=12, ge=1, le=60)
    max_cash_budget: float | None = Field(default=None, ge=0)
    currency: Literal["USD"] = "USD"
    rule_version: str = "financial_rules_v1.0"
    task_id: str | None = None
    item_id: str | None = None


class FinancialMetrics(StrictModel):
    """Calculated deterministic financial metrics."""

    fixed_costs: float
    variable_cost_per_unit: float
    unit_contribution_margin: float
    gross_margin_rate: float
    initial_batch_cash: float
    amortized_mold_cost_per_unit: float
    mold_cost_ratio: float
    monthly_contribution: float
    break_even_units: int | None
    payback_months: float
    estimated_12m_roi: float


class BreakEvenPoint(StrictModel):
    """Monthly cash flow and break-even projection point."""

    month: int
    cumulative_units: int
    cumulative_revenue: float
    cumulative_cost: float
    net_cashflow: float
    is_break_even: bool


class SensitivityPoint(StrictModel):
    """Sensitivity analysis point under sales/price variation."""

    sales_change_percent: float
    price_change_percent: float
    payback_months: float
    is_vetoed: bool


class AlternativeSuggestion(StrictModel):
    """Actionable alternative recommendation when vetoed."""

    suggestion_id: str
    title: str
    description: str
    estimated_impact: str
    suggested_params: dict[str, Any]


class FinancialEvaluateResponse(StrictModel):
    """Deterministic financial evaluation result and circuit breaker state."""

    financial_state: FinancialState
    circuit_breaker_triggered: bool
    rule_version: str
    currency: str
    evaluated_at: UtcDateTime
    reasons: list[str]
    triggered_rules: list[str]
    metrics: FinancialMetrics | None
    break_even_timeline: list[BreakEvenPoint]
    sensitivity_matrix: list[SensitivityPoint]
    alternative_suggestions: list[AlternativeSuggestion]
    applied_assumptions: dict[str, Any]


class FinancialRuleItem(StrictModel):
    """Specification of one deterministic veto rule."""

    code: str
    name: str
    description: str
    threshold: str


class FinancialRuleInfo(StrictModel):
    """Metadata describing active financial veto rules."""

    rule_version: str
    rules: list[FinancialRuleItem]


T = TypeVar("T")


class Page[T](StrictModel):
    """Cursor-paginated result."""

    items: list[T]
    next_cursor: str | None


class SuccessEnvelope[T](StrictModel):
    """Standard successful API envelope."""

    code: Literal[0] = 0
    message: Literal["ok"] = "ok"
    data: T
