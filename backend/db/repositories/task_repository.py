"""Repository for insight tasks (production TaskStore backend)."""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import InsightTaskModel
from runtime.task_store import TaskOptions, TaskRecord, TaskStatus, TaskSummary


def _iso(dt: datetime | None) -> str | None:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ") if dt else None


def to_record(model: InsightTaskModel) -> TaskRecord:
    return TaskRecord(
        task_id=model.task_id,
        asin=model.asin,
        product_id=str(model.product_id) if model.product_id else None,
        platform=model.platform,
        marketplace=model.marketplace,
        status=TaskStatus(model.status),
        current_node=model.current_node,
        progress=model.progress,
        retry_count=model.retry_count,
        review_window_months=model.review_window_months,
        max_reviews=model.max_reviews,
        financial_constraint=model.financial_constraint or {},
        options=TaskOptions(**(model.options or {})),
        summary=TaskSummary(**(model.summary or {})),
        final_report=model.final_report,
        error_message=model.error_message,
        created_at=_iso(model.created_at),
        started_at=_iso(model.started_at),
        finished_at=_iso(model.finished_at),
    )


def to_model(record: TaskRecord) -> InsightTaskModel:
    return InsightTaskModel(
        task_id=record.task_id,
        asin=record.asin,
        product_id=uuid.UUID(record.product_id) if record.product_id else None,
        platform=record.platform,
        marketplace=record.marketplace,
        status=record.status.value,
        current_node=record.current_node,
        progress=record.progress,
        retry_count=record.retry_count,
        review_window_months=record.review_window_months,
        max_reviews=record.max_reviews,
        financial_constraint=record.financial_constraint,
        options=record.options.model_dump(),
        summary=record.summary.model_dump(),
        final_report=record.final_report,
        error_message=record.error_message,
    )


def _parse_dt(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
        except ValueError:
            return value
    return value


SIMPLE_FIELDS = {"current_node", "progress", "retry_count", "final_report", "error_message"}


class TaskRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, record: TaskRecord) -> TaskRecord:
        self.session.add(to_model(record))
        await self.session.commit()
        return record

    async def get(self, task_id: str) -> TaskRecord | None:
        row = await self.session.scalar(
            select(InsightTaskModel).where(InsightTaskModel.task_id == task_id)
        )
        return to_record(row) if row else None

    async def update(self, task_id: str, fields: dict[str, Any]) -> TaskRecord | None:
        values: dict[str, Any] = {}
        for key, value in fields.items():
            if key == "status":
                values["status"] = value.value if isinstance(value, TaskStatus) else str(value)
            elif key == "summary":
                values["summary"] = value if isinstance(value, dict) else value.model_dump()
            elif key in SIMPLE_FIELDS:
                values[key] = value
            elif key in ("started_at", "finished_at"):
                values[key] = _parse_dt(value)
        if not values:
            return await self.get(task_id)
        await self.session.execute(
            update(InsightTaskModel).where(InsightTaskModel.task_id == task_id).values(**values)
        )
        await self.session.commit()
        return await self.get(task_id)

    async def list(
        self,
        status: TaskStatus | None = None,
        asin: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[TaskRecord], int]:
        stmt = select(InsightTaskModel)
        if status is not None:
            stmt = stmt.where(InsightTaskModel.status == (status.value if isinstance(status, TaskStatus) else str(status)))
        if asin is not None:
            stmt = stmt.where(InsightTaskModel.asin == asin)
        total = await self.session.scalar(
            select(func.count()).select_from(stmt.subquery())
        )
        rows = (
            await self.session.scalars(
                stmt.order_by(InsightTaskModel.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        ).all()
        return [to_record(r) for r in rows], int(total or 0)
