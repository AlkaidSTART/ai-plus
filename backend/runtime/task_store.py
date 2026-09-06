"""Task state storage.

`TaskStore` is the production-facing interface. Implementations:

- :class:`InMemoryTaskStore` — used by tests and offline demo runs.
- A PostgreSQL-backed store (via repositories) is wired in the workflow step
  and remains the production main path.
"""

import asyncio
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class TaskStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELED = "CANCELED"


class TaskOptions(BaseModel):
    enable_vision_audit: bool = True
    enable_backtest: bool = False


class TaskSummary(BaseModel):
    review_count: int | None = None
    cluster_count: int | None = None
    proposal_count: int | None = None
    veto_status: str = "PENDING"
    backtest_score: float | None = None
    avg_rating: float | None = None
    negative_review_rate: float | None = None


class TaskRecord(BaseModel):
    task_id: str
    asin: str
    product_id: str | None = None
    platform: str = "amazon"
    marketplace: str = "US"
    status: TaskStatus = TaskStatus.PENDING
    current_node: str | None = None
    progress: int = 0
    retry_count: int = 0
    review_window_months: int = 6
    max_reviews: int = 500
    financial_constraint: dict[str, Any] = Field(default_factory=dict)
    options: TaskOptions = Field(default_factory=TaskOptions)
    summary: TaskSummary = Field(default_factory=TaskSummary)
    final_report: dict[str, Any] | None = None
    error_message: str | None = None
    created_at: str | None = None
    started_at: str | None = None
    finished_at: str | None = None

    model_config = {"validate_assignment": True}


class TaskStore:
    async def create(self, task: TaskRecord) -> TaskRecord:  # pragma: no cover - interface
        raise NotImplementedError

    async def get(self, task_id: str) -> TaskRecord | None:  # pragma: no cover - interface
        raise NotImplementedError

    async def update(self, task_id: str, **fields: Any) -> TaskRecord | None:  # pragma: no cover
        raise NotImplementedError

    async def list(
        self,
        status: TaskStatus | None = None,
        asin: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[TaskRecord], int]:  # pragma: no cover - interface
        raise NotImplementedError


class InMemoryTaskStore(TaskStore):
    def __init__(self) -> None:
        self._tasks: dict[str, TaskRecord] = {}
        self._lock = asyncio.Lock()

    async def create(self, task: TaskRecord) -> TaskRecord:
        async with self._lock:
            self._tasks[task.task_id] = task.model_copy()
        return task

    async def get(self, task_id: str) -> TaskRecord | None:
        async with self._lock:
            task = self._tasks.get(task_id)
            return task.model_copy() if task else None

    async def update(self, task_id: str, **fields: Any) -> TaskRecord | None:
        async with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return None
            for key, value in fields.items():
                setattr(task, key, value)
            self._tasks[task_id] = task
            return task.model_copy()

    async def list(
        self,
        status: TaskStatus | None = None,
        asin: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[TaskRecord], int]:
        async with self._lock:
            items = [
                t.model_copy()
                for t in self._tasks.values()
                if (status is None or t.status == status) and (asin is None or t.asin == asin)
            ]
        items.sort(key=lambda t: t.created_at or "", reverse=True)
        total = len(items)
        start = (page - 1) * page_size
        return items[start : start + page_size], total
