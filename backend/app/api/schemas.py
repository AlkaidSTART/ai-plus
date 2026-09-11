"""P0 公共模型：状态枚举与请求/响应 schema，对齐 api.md §2/§4/§5。"""

from datetime import date, datetime
from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELED = "CANCELED"


class NodeStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELED = "CANCELED"
    SKIPPED = "SKIPPED"


class VetoStatus(str, Enum):
    NOT_EVALUATED = "NOT_EVALUATED"
    PASSED = "PASSED"
    VETOED = "VETOED"


class Availability(str, Enum):
    SUFFICIENT = "SUFFICIENT"
    LIMITED = "LIMITED"
    INSUFFICIENT = "INSUFFICIENT"


class ProposalColumn(str, Enum):
    PRODUCT = "PRODUCT"
    PACKAGING = "PACKAGING"


class Phase(str, Enum):
    P0 = "P0"


class Window(BaseModel):
    start_date: date
    end_date: date


class CreateTaskRequest(BaseModel):
    project_id: str
    asins: list[str] = Field(min_length=1, max_length=10)
    platform: str = "amazon"
    marketplace: str = "US"
    window: Optional[Window] = None


class TaskItemState(BaseModel):
    item_id: str
    asin: str
    status: TaskStatus
    attempt: int = 1
    current_node: Optional[str] = None
    report_id: Optional[str] = None
    error: Optional[dict[str, Any]] = None


class Metric(BaseModel):
    value: Optional[float] = None
    reason: Optional[str] = None
    basis: Optional[dict[str, Any]] = None


class Cluster(BaseModel):
    id: str
    name_zh: str
    name_en: str
    category: Literal[
        "quality", "function", "size", "accessory", "instructions", "packaging", "other"
    ]
    frequency: int
    denominator: int
    share_ratio: Optional[float] = None
    severity: int = Field(ge=1, le=5)
    severity_reason: str
    evidence_count: int
    photo_count: int = 0


class Proposal(BaseModel):
    id: str
    column: ProposalColumn
    title: str
    action: str
    target_cluster_ids: list[str] = Field(min_length=1)
    expected_effect: str
    assumptions: list[str] = []
    verification_required: list[str] = []
    evidence_count: int
    photo_count: int = 0


class RetryRequest(BaseModel):
    item_ids: list[str]


class TaskItemCreated(BaseModel):
    item_id: str
    asin: str
    status: TaskStatus


class TaskLinks(BaseModel):
    self: str
    events: str


class TaskCreatedResponse(BaseModel):
    task_id: str
    status: TaskStatus
    phase: Phase
    reused: bool
    window: Window
    items: list[TaskItemCreated]
    links: TaskLinks


class RetryTaskResponse(TaskCreatedResponse):
    parent_task_id: str


class NodeState(BaseModel):
    key: str
    status: NodeStatus
    duration_ms: Optional[int] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    output_summary: Optional[dict[str, Any]] = None
    skip_reason: Optional[str] = None


class ItemProgress(BaseModel):
    completed_nodes: int
    total_nodes: int
    processed_reviews: int
    total_reviews: Optional[int] = None


class TaskItemSnapshot(BaseModel):
    item_id: str
    asin: str
    status: TaskStatus
    attempt: int = 1
    current_node: Optional[str] = None
    nodes: list[NodeState] = []
    progress: Optional[ItemProgress] = None
    report_id: Optional[str] = None
    error: Optional[dict[str, Any]] = None


class WarningItem(BaseModel):
    code: str
    message: str
    item_id: Optional[str] = None


class TaskSnapshotResponse(BaseModel):
    task_id: str
    project_id: str
    phase: Phase
    status: TaskStatus
    created_at: datetime
    completed_at: Optional[datetime] = None
    cancel_requested_at: Optional[datetime] = None
    last_event_id: str
    item_counts: dict[str, int]
    items: list[TaskItemSnapshot]
    warnings: list[WarningItem] = []


class TaskListItem(BaseModel):
    task_id: str
    project_id: str
    created_at: datetime
    status: TaskStatus
    asins: list[str]
    item_counts: dict[str, int]
    warnings_count: int


class TaskListResponse(BaseModel):
    items: list[TaskListItem]
    next_cursor: Optional[str] = None


class CancelResponse(BaseModel):
    task_id: str
    status: TaskStatus
    cancel_requested_at: Optional[datetime] = None
