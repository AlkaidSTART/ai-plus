"""Task persistence and query services for the P0 API."""

from __future__ import annotations

import base64
import hashlib
import json
import re
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any, Literal, cast
from uuid import uuid4

from sqlalchemy import Select, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from insightx.database import SessionFactory
from insightx.errors import ApiError
from insightx.models import (
    Evidence,
    EvidenceClaimRef,
    IdempotencyRecord,
    OutboxMessage,
    Report,
    Task,
    TaskEvent,
    TaskItem,
    utc_now,
)
from insightx.schemas import (
    DataQuality,
    EvidenceResponse,
    EvidenceSourceType,
    FinancialState,
    NodeProgress,
    Page,
    ReportPainPoint,
    ReportProposal,
    ReportResponse,
    ReportWarning,
    RetryTaskRequest,
    SampleMetrics,
    TaskCreatedItem,
    TaskCreatedResponse,
    TaskCreateRequest,
    TaskError,
    TaskItemSnapshot,
    TaskListItem,
    TaskProgress,
    TaskSnapshot,
    TaskStatus,
    TaskWindow,
)
from insightx.services.export import export_task_charter_zip

_TERMINAL_TASK_STATUSES = {
    TaskStatus.COMPLETED,
    TaskStatus.FAILED,
    TaskStatus.CANCELED,
}
_TERMINAL_ITEM_STATUSES = {
    TaskStatus.COMPLETED,
    TaskStatus.FAILED,
    TaskStatus.CANCELED,
}
_SSE_EVENT_TYPES = {
    "task.status_changed",
    "task_item.status_changed",
    "task_item.node_progress",
}
_TASK_CREATE_SCOPE = "task.create"
_TASK_RETRY_SCOPE = "task.retry"


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


def _request_hash(payload: dict[str, Any]) -> str:
    canonical = json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _window_preset(value: str) -> Literal["1m", "3m", "6m"]:
    if value not in {"1m", "3m", "6m"}:
        raise ValueError(f"Unsupported window preset: {value}")
    return cast(Literal["1m", "3m", "6m"], value)


def _task_window(task: Task) -> TaskWindow:
    return TaskWindow(preset=_window_preset(task.window_preset))


def _encode_cursor(created_at: datetime, resource_id: str) -> str:
    raw = f"{created_at.isoformat()}|{resource_id}".encode()
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _decode_cursor(
    cursor: str,
    *,
    resource_name: str,
) -> tuple[datetime, str]:
    try:
        padding = "=" * (-len(cursor) % 4)
        decoded = base64.urlsafe_b64decode(f"{cursor}{padding}").decode("utf-8")
        timestamp_text, resource_id = decoded.split("|", maxsplit=1)
        created_at = datetime.fromisoformat(timestamp_text)
        if created_at.tzinfo is None or not resource_id:
            raise ValueError("Cursor must contain a UTC timestamp and ID.")
    except (ValueError, UnicodeDecodeError) as exc:
        raise ApiError(
            422,
            "VALIDATION_ERROR",
            f"Invalid {resource_name} cursor.",
        ) from exc
    return created_at.astimezone(UTC), resource_id


def _get_task_or_404(
    session: Session,
    *,
    tenant_id: str,
    task_id: str,
) -> Task:
    task = session.scalar(
        select(Task).where(
            Task.tenant_id == tenant_id,
            Task.task_id == task_id,
        )
    )
    if task is None:
        raise ApiError(404, "TASK_NOT_FOUND", "Task not found.")
    return task


def _get_item_or_404(
    session: Session,
    *,
    tenant_id: str,
    task_id: str,
    item_id: str,
) -> TaskItem:
    item = session.scalar(
        select(TaskItem).where(
            TaskItem.tenant_id == tenant_id,
            TaskItem.task_id == task_id,
            TaskItem.item_id == item_id,
        )
    )
    if item is None:
        raise ApiError(404, "ITEM_NOT_FOUND", "Task item not found.")
    return item


def _task_items(
    session: Session,
    *,
    tenant_id: str,
    task_id: str,
) -> list[TaskItem]:
    return list(
        session.scalars(
            select(TaskItem)
            .where(
                TaskItem.tenant_id == tenant_id,
                TaskItem.task_id == task_id,
            )
            .order_by(TaskItem.created_at.asc(), TaskItem.item_id.asc())
        ).all()
    )


def _task_item_counts(
    session: Session,
    *,
    tenant_id: str,
    task_ids: Sequence[str],
) -> dict[str, dict[str, int]]:
    counts: dict[str, dict[str, int]] = {
        task_id: {"total": 0, "completed": 0, "failed": 0, "canceled": 0}
        for task_id in task_ids
    }
    if not task_ids:
        return counts
    rows = session.execute(
        select(TaskItem.task_id, TaskItem.status, func.count())
        .where(
            TaskItem.tenant_id == tenant_id,
            TaskItem.task_id.in_(task_ids),
        )
        .group_by(TaskItem.task_id, TaskItem.status)
    ).all()
    for row in rows:
        task_id = str(row[0])
        status = str(row[1])
        count = int(row[2])
        task_counts = counts[task_id]
        task_counts["total"] += count
        if status == TaskStatus.COMPLETED:
            task_counts["completed"] += count
        elif status == TaskStatus.FAILED:
            task_counts["failed"] += count
        elif status == TaskStatus.CANCELED:
            task_counts["canceled"] += count
    return counts


def _last_event_ids(
    session: Session,
    *,
    tenant_id: str,
    task_ids: Sequence[str],
) -> dict[str, int]:
    if not task_ids:
        return {}
    rows = session.execute(
        select(TaskEvent.task_id, func.max(TaskEvent.event_id))
        .join(Task, Task.task_id == TaskEvent.task_id)
        .where(
            Task.tenant_id == tenant_id,
            TaskEvent.task_id.in_(task_ids),
        )
        .group_by(TaskEvent.task_id)
    ).all()
    return {str(row[0]): int(row[1]) for row in rows}


def _build_task_list_items(
    session: Session,
    tasks: Sequence[Task],
    *,
    tenant_id: str,
) -> list[TaskListItem]:
    task_ids = [task.task_id for task in tasks]
    counts = _task_item_counts(
        session,
        tenant_id=tenant_id,
        task_ids=task_ids,
    )
    last_event_ids = _last_event_ids(
        session,
        tenant_id=tenant_id,
        task_ids=task_ids,
    )
    return [
        TaskListItem(
            task_id=task.task_id,
            status=TaskStatus(task.status),
            platform=task.platform,
            marketplace=task.marketplace,
            window=_task_window(task),
            created_at=task.created_at,
            updated_at=task.updated_at,
            total_items=counts[task.task_id]["total"],
            completed_items=counts[task.task_id]["completed"],
            failed_items=counts[task.task_id]["failed"],
            canceled_items=counts[task.task_id]["canceled"],
            last_event_id=(
                str(last_event_ids[task.task_id])
                if task.task_id in last_event_ids
                else None
            ),
        )
        for task in tasks
    ]


def _build_snapshot(
    session: Session,
    task: Task,
) -> TaskSnapshot:
    summary = _build_task_list_items(
        session,
        [task],
        tenant_id=task.tenant_id,
    )[0]
    items = _task_items(
        session,
        tenant_id=task.tenant_id,
        task_id=task.task_id,
    )
    item_ids = [item.item_id for item in items]
    report_item_ids = set(
        session.scalars(
            select(Report.item_id).where(
                Report.tenant_id == task.tenant_id,
                Report.task_id == task.task_id,
            )
        ).all()
    )
    node_events: list[TaskEvent] = []
    if item_ids:
        node_events = list(
            session.scalars(
                select(TaskEvent)
                .join(Task, Task.task_id == TaskEvent.task_id)
                .where(
                    Task.tenant_id == task.tenant_id,
                    TaskEvent.task_id == task.task_id,
                    TaskEvent.task_item_id.in_(item_ids),
                    TaskEvent.event_type == "task_item.node_progress",
                )
                .order_by(TaskEvent.event_id.asc())
            ).all()
        )
    nodes_by_item: dict[str, dict[str, NodeProgress]] = {
        item_id: {} for item_id in item_ids
    }
    for event in node_events:
        if event.task_item_id is None or not isinstance(event.payload, dict):
            continue
        payload = event.payload
        try:
            node = NodeProgress.model_validate(
                {
                    "node_id": payload["node_id"],
                    "node_name": payload["node_name"],
                    "status": payload["status"],
                    "started_at": payload.get("started_at"),
                    "finished_at": payload.get("finished_at"),
                    "duration_ms": payload.get("duration_ms"),
                    "skip_reason": payload.get("skip_reason"),
                    "error": payload.get("error"),
                }
            )
        except (KeyError, ValueError):
            continue
        nodes_by_item[event.task_item_id][node.node_id] = node

    item_snapshots = [
        TaskItemSnapshot(
            item_id=item.item_id,
            asin=item.asin,
            status=TaskStatus(item.status),
            current_node=item.current_node,
            attempt=item.attempt,
            data_quality=(
                DataQuality(item.data_quality)
                if item.data_quality is not None
                else None
            ),
            sample_metrics=(
                SampleMetrics.model_validate(item.sample_metrics)
                if item.sample_metrics is not None
                else None
            ),
            nodes=list(nodes_by_item[item.item_id].values()),
            error=(
                TaskError.model_validate(item.error) if item.error is not None else None
            ),
            report_available=item.item_id in report_item_ids,
        )
        for item in items
    ]
    finished_items = sum(
        TaskStatus(item.status) in _TERMINAL_ITEM_STATUSES for item in items
    )
    return TaskSnapshot(
        **summary.model_dump(),
        parent_task_id=task.parent_task_id,
        cancel_requested_at=task.cancel_requested_at,
        finished_at=task.finished_at,
        items=item_snapshots,
        progress=TaskProgress(
            total_items=len(items),
            finished_items=finished_items,
        ),
    )


def _created_response(
    session: Session,
    task: Task,
    *,
    reused: bool,
) -> TaskCreatedResponse:
    items = _task_items(
        session,
        tenant_id=task.tenant_id,
        task_id=task.task_id,
    )
    return TaskCreatedResponse(
        task_id=task.task_id,
        status=TaskStatus(task.status),
        reused=reused,
        parent_task_id=task.parent_task_id,
        created_at=task.created_at,
        items=[
            TaskCreatedItem(
                item_id=item.item_id,
                asin=item.asin,
                status=TaskStatus(item.status),
            )
            for item in items
        ],
    )


def _persist_task(
    session: Session,
    *,
    tenant_id: str,
    platform: str,
    marketplace: str,
    window_preset: str,
    asins: Sequence[str],
    parent_task_id: str | None,
) -> tuple[Task, list[TaskItem]]:
    now = utc_now()
    task = Task(
        task_id=_new_id("tsk"),
        tenant_id=tenant_id,
        parent_task_id=parent_task_id,
        platform=platform,
        marketplace=marketplace,
        window_preset=window_preset,
        status=TaskStatus.QUEUED.value,
        created_at=now,
        updated_at=now,
    )
    session.add(task)
    session.flush()
    items = [
        TaskItem(
            item_id=_new_id("itm"),
            task_id=task.task_id,
            tenant_id=tenant_id,
            asin=asin,
            status=TaskStatus.QUEUED.value,
            current_node=None,
            attempt=1,
            data_quality=None,
            sample_metrics=None,
            error=None,
            created_at=now,
            updated_at=now,
        )
        for asin in asins
    ]
    session.add_all(items)
    session.flush()

    session.add(
        TaskEvent(
            task_id=task.task_id,
            task_item_id=None,
            event_type="task.status_changed",
            payload={"status": TaskStatus.QUEUED.value},
            created_at=now,
        )
    )
    for item in items:
        session.add(
            TaskEvent(
                task_id=task.task_id,
                task_item_id=item.item_id,
                event_type="task_item.status_changed",
                payload={"status": TaskStatus.QUEUED.value},
                created_at=now,
            )
        )
    session.add(
        OutboxMessage(
            message_id=_new_id("msg"),
            tenant_id=tenant_id,
            topic="task.created",
            aggregate_id=task.task_id,
            payload={"task_id": task.task_id},
            status="PENDING",
            available_at=now,
            attempts=0,
            created_at=now,
        )
    )
    return task, items


def _reuse_idempotent_task(
    session: Session,
    *,
    tenant_id: str,
    scope: str,
    key: str,
    request_hash: str,
) -> TaskCreatedResponse:
    record = session.scalar(
        select(IdempotencyRecord)
        .where(
            IdempotencyRecord.tenant_id == tenant_id,
            IdempotencyRecord.scope == scope,
            IdempotencyRecord.key == key,
        )
        .with_for_update()
    )
    if record is None:
        raise ApiError(
            409,
            "IDEMPOTENCY_CONFLICT",
            "The idempotency key is already in use.",
        )
    if record.request_hash != request_hash:
        raise ApiError(
            409,
            "IDEMPOTENCY_CONFLICT",
            "The idempotency key was used with a different request.",
        )
    task = session.scalar(
        select(Task).where(
            Task.task_id == record.resource_id,
            Task.tenant_id == tenant_id,
        )
    )
    if task is None:
        raise ApiError(
            409,
            "IDEMPOTENCY_CONFLICT",
            "The idempotent resource is no longer available.",
        )
    return _created_response(session, task, reused=True)


def create_task(
    session: Session,
    *,
    tenant_id: str,
    request: TaskCreateRequest,
    idempotency_key: str,
) -> TaskCreatedResponse:
    """Create a task aggregate or replay a matching idempotent request."""

    payload = request.model_dump(mode="json")
    request_hash = _request_hash(payload)
    try:
        with session.begin():
            existing = session.scalar(
                select(IdempotencyRecord).where(
                    IdempotencyRecord.tenant_id == tenant_id,
                    IdempotencyRecord.scope == _TASK_CREATE_SCOPE,
                    IdempotencyRecord.key == idempotency_key,
                )
            )
            if existing is not None:
                return _reuse_idempotent_task(
                    session,
                    tenant_id=tenant_id,
                    scope=_TASK_CREATE_SCOPE,
                    key=idempotency_key,
                    request_hash=request_hash,
                )

            target_asins = list(request.asins)
            if not target_asins and request.keyword:
                from insightx.services.search import search_amazon_products_sync

                products = search_amazon_products_sync(request.keyword, limit=10)
                target_asins = [p["asin"] for p in products if p.get("asin")]

            task, _ = _persist_task(
                session,
                tenant_id=tenant_id,
                platform=request.platform,
                marketplace=request.marketplace,
                window_preset=request.window.preset,
                asins=target_asins,
                parent_task_id=None,
            )
            session.add(
                IdempotencyRecord(
                    record_id=_new_id("idr"),
                    tenant_id=tenant_id,
                    scope=_TASK_CREATE_SCOPE,
                    key=idempotency_key,
                    request_hash=request_hash,
                    response_status=202,
                    resource_id=task.task_id,
                    created_at=utc_now(),
                )
            )
            session.flush()
            return _created_response(session, task, reused=False)
    except IntegrityError:
        session.rollback()
        with session.begin():
            return _reuse_idempotent_task(
                session,
                tenant_id=tenant_id,
                scope=_TASK_CREATE_SCOPE,
                key=idempotency_key,
                request_hash=request_hash,
            )


def list_tasks(
    session: Session,
    *,
    tenant_id: str,
    status: TaskStatus | None,
    cursor: str | None,
    limit: int,
) -> Page[TaskListItem]:
    """Return a stable, cursor-paginated task list for one tenant."""

    statement: Select[tuple[Task]] = select(Task).where(Task.tenant_id == tenant_id)
    if status is not None:
        statement = statement.where(Task.status == status.value)
    if cursor is not None:
        created_at, task_id = _decode_cursor(cursor, resource_name="task")
        statement = statement.where(
            (Task.created_at < created_at)
            | ((Task.created_at == created_at) & (Task.task_id < task_id))
        )
    tasks = list(
        session.scalars(
            statement.order_by(Task.created_at.desc(), Task.task_id.desc()).limit(
                limit + 1
            )
        ).all()
    )
    has_next = len(tasks) > limit
    page_tasks = tasks[:limit]
    next_cursor = None
    if has_next and page_tasks:
        last = page_tasks[-1]
        next_cursor = _encode_cursor(last.created_at, last.task_id)
    return Page(
        items=_build_task_list_items(
            session,
            page_tasks,
            tenant_id=tenant_id,
        ),
        next_cursor=next_cursor,
    )


def get_task_snapshot(
    session: Session,
    *,
    tenant_id: str,
    task_id: str,
) -> TaskSnapshot:
    """Return a point-in-time snapshot for one tenant-scoped task."""

    task = _get_task_or_404(
        session,
        tenant_id=tenant_id,
        task_id=task_id,
    )
    return _build_snapshot(session, task)


def cancel_task(
    session: Session,
    *,
    tenant_id: str,
    task_id: str,
) -> tuple[TaskSnapshot, bool]:
    """Record the first cancellation request without changing task state."""

    with session.begin():
        task = _get_task_or_404(
            session,
            tenant_id=tenant_id,
            task_id=task_id,
        )
        if TaskStatus(task.status) in _TERMINAL_TASK_STATUSES:
            return _build_snapshot(session, task), False
        if task.cancel_requested_at is not None:
            return _build_snapshot(session, task), False
        now = utc_now()
        task.cancel_requested_at = now
        task.updated_at = now
        session.flush()
        return _build_snapshot(session, task), True


def retry_task(
    session: Session,
    *,
    tenant_id: str,
    task_id: str,
    request: RetryTaskRequest,
    idempotency_key: str,
) -> TaskCreatedResponse:
    """Create a new task for selected failed items from a terminal task."""

    payload = {"task_id": task_id, **request.model_dump(mode="json")}
    request_hash = _request_hash(payload)
    try:
        with session.begin():
            existing = session.scalar(
                select(IdempotencyRecord).where(
                    IdempotencyRecord.tenant_id == tenant_id,
                    IdempotencyRecord.scope == _TASK_RETRY_SCOPE,
                    IdempotencyRecord.key == idempotency_key,
                )
            )
            if existing is not None:
                return _reuse_idempotent_task(
                    session,
                    tenant_id=tenant_id,
                    scope=_TASK_RETRY_SCOPE,
                    key=idempotency_key,
                    request_hash=request_hash,
                )

            source_task = _get_task_or_404(
                session,
                tenant_id=tenant_id,
                task_id=task_id,
            )
            if TaskStatus(source_task.status) not in _TERMINAL_TASK_STATUSES:
                raise ApiError(
                    409,
                    "ITEM_NOT_RETRYABLE",
                    "Only failed items from a terminal task can be retried.",
                )
            items = list(
                session.scalars(
                    select(TaskItem).where(
                        TaskItem.tenant_id == tenant_id,
                        TaskItem.task_id == task_id,
                        TaskItem.item_id.in_(request.item_ids),
                    )
                ).all()
            )
            items_by_id = {item.item_id: item for item in items}
            if len(items_by_id) != len(request.item_ids) or any(
                TaskStatus(items_by_id[item_id].status) != TaskStatus.FAILED
                for item_id in request.item_ids
            ):
                raise ApiError(
                    409,
                    "ITEM_NOT_RETRYABLE",
                    "Only failed items from the source task can be retried.",
                )
            ordered_items = [items_by_id[item_id] for item_id in request.item_ids]
            new_task, _ = _persist_task(
                session,
                tenant_id=tenant_id,
                platform=source_task.platform,
                marketplace=source_task.marketplace,
                window_preset=source_task.window_preset,
                asins=[item.asin for item in ordered_items],
                parent_task_id=source_task.task_id,
            )
            session.add(
                IdempotencyRecord(
                    record_id=_new_id("idr"),
                    tenant_id=tenant_id,
                    scope=_TASK_RETRY_SCOPE,
                    key=idempotency_key,
                    request_hash=request_hash,
                    response_status=202,
                    resource_id=new_task.task_id,
                    created_at=utc_now(),
                )
            )
            session.flush()
            return _created_response(session, new_task, reused=False)
    except IntegrityError:
        session.rollback()
        with session.begin():
            return _reuse_idempotent_task(
                session,
                tenant_id=tenant_id,
                scope=_TASK_RETRY_SCOPE,
                key=idempotency_key,
                request_hash=request_hash,
            )


def get_report(
    session: Session,
    *,
    tenant_id: str,
    task_id: str,
    item_id: str,
) -> ReportResponse:
    """Return a persisted report or report that it is not ready."""

    _get_task_or_404(session, tenant_id=tenant_id, task_id=task_id)
    item = _get_item_or_404(
        session,
        tenant_id=tenant_id,
        task_id=task_id,
        item_id=item_id,
    )
    report = session.scalar(
        select(Report).where(
            Report.tenant_id == tenant_id,
            Report.task_id == task_id,
            Report.item_id == item_id,
        )
    )
    if report is None:
        raise ApiError(
            409,
            "REPORT_NOT_READY",
            "The report is not ready.",
            retryable=True,
        )
    return ReportResponse(
        report_id=report.report_id,
        task_id=report.task_id,
        item_id=report.item_id,
        asin=item.asin,
        data_quality=DataQuality(report.data_quality),
        sample_metrics=SampleMetrics.model_validate(report.sample_metrics),
        generated_at=report.generated_at,
        financial_state=FinancialState(report.financial_state),
        pain_points=[
            ReportPainPoint.model_validate(pain_point)
            for pain_point in report.pain_points
        ],
        proposals=[
            ReportProposal.model_validate(proposal) for proposal in report.proposals
        ],
        warnings=[ReportWarning.model_validate(warning) for warning in report.warnings],
        model_metadata=report.model_metadata,
    )


def _decode_evidence_cursor(cursor: str) -> tuple[datetime, str]:
    return _decode_cursor(cursor, resource_name="evidence")


def list_evidence(
    session: Session,
    *,
    tenant_id: str,
    task_id: str,
    item_id: str,
    claim_id: str | None,
    source_type: EvidenceSourceType | None,
    cursor: str | None,
    limit: int,
) -> Page[EvidenceResponse]:
    """Return evidence scoped to one accessible task item."""

    _get_task_or_404(session, tenant_id=tenant_id, task_id=task_id)
    _get_item_or_404(
        session,
        tenant_id=tenant_id,
        task_id=task_id,
        item_id=item_id,
    )
    statement: Select[tuple[Evidence]] = select(Evidence).where(
        Evidence.tenant_id == tenant_id,
        Evidence.task_id == task_id,
        Evidence.item_id == item_id,
    )
    if source_type is not None:
        statement = statement.where(Evidence.source_type == source_type.value)
    if claim_id is not None:
        statement = statement.where(
            Evidence.evidence_id.in_(
                select(EvidenceClaimRef.evidence_id)
                .join(
                    Evidence,
                    Evidence.evidence_id == EvidenceClaimRef.evidence_id,
                )
                .where(
                    EvidenceClaimRef.claim_id == claim_id,
                    Evidence.tenant_id == tenant_id,
                    Evidence.task_id == task_id,
                    Evidence.item_id == item_id,
                )
            )
        )
    if cursor is not None:
        created_at, evidence_id = _decode_evidence_cursor(cursor)
        statement = statement.where(
            (Evidence.created_at < created_at)
            | (
                (Evidence.created_at == created_at)
                & (Evidence.evidence_id < evidence_id)
            )
        )
    evidence_rows = list(
        session.scalars(
            statement.order_by(
                Evidence.created_at.desc(),
                Evidence.evidence_id.desc(),
            ).limit(limit + 1)
        ).all()
    )
    has_next = len(evidence_rows) > limit
    page_rows = evidence_rows[:limit]
    next_cursor = None
    if has_next and page_rows:
        last = page_rows[-1]
        next_cursor = _encode_cursor(last.created_at, last.evidence_id)
    return Page(
        items=[
            EvidenceResponse(
                evidence_id=evidence.evidence_id,
                source_type=EvidenceSourceType(evidence.source_type),
                source_ref=evidence.source_ref,
                excerpt=evidence.excerpt,
                source_url=evidence.source_url,
                published_at=evidence.published_at,
                metadata=evidence.source_metadata,
                provenance=evidence.provenance,
            )
            for evidence in page_rows
        ],
        next_cursor=next_cursor,
    )


def parse_event_cursor(cursor: str | None) -> int:
    """Parse the opaque SSE replay cursor."""

    if cursor is None:
        return 0
    if not re.fullmatch(r"[0-9]+", cursor):
        raise ApiError(
            422,
            "INVALID_EVENT_CURSOR",
            "Invalid event cursor.",
        )
    return int(cursor)


def prepare_event_stream(
    session_factory: SessionFactory,
    *,
    tenant_id: str,
    task_id: str,
    cursor: str | None,
) -> int:
    """Validate task access and the requested SSE cursor before streaming."""

    requested = parse_event_cursor(cursor)
    with session_factory() as session:
        _get_task_or_404(
            session,
            tenant_id=tenant_id,
            task_id=task_id,
        )
        max_event_id = session.scalar(
            select(func.max(TaskEvent.event_id))
            .join(Task, Task.task_id == TaskEvent.task_id)
            .where(
                Task.tenant_id == tenant_id,
                TaskEvent.task_id == task_id,
            )
        )
        latest = int(max_event_id or 0)
        if requested > latest:
            raise ApiError(
                422,
                "INVALID_EVENT_CURSOR",
                "The event cursor is outside the retained range.",
            )
    return requested


def fetch_task_events(
    session_factory: SessionFactory,
    *,
    task_id: str,
    after_event_id: int,
    limit: int = 100,
    tenant_id: str | None = None,
) -> list[dict[str, Any]]:
    """Load one ordered batch of SSE event envelopes."""

    with session_factory() as session:
        if tenant_id is None:
            tenant_id = session.scalar(
                select(Task.tenant_id).where(Task.task_id == task_id)
            )
        if tenant_id is None:
            return []
        events = list(
            session.scalars(
                select(TaskEvent)
                .join(Task, Task.task_id == TaskEvent.task_id)
                .where(
                    Task.tenant_id == tenant_id,
                    TaskEvent.task_id == task_id,
                    TaskEvent.event_id > after_event_id,
                    TaskEvent.event_type.in_(_SSE_EVENT_TYPES),
                )
                .order_by(TaskEvent.event_id.asc())
                .limit(limit)
            ).all()
        )
        return [
            {
                "version": 1,
                "id": str(event.event_id),
                "type": event.event_type,
                "task_id": event.task_id,
                "task_item_id": event.task_item_id,
                "time": event.created_at.astimezone(UTC)
                .isoformat()
                .replace("+00:00", "Z"),
                "payload": event.payload if isinstance(event.payload, dict) else {},
            }
            for event in events
        ]


def task_is_terminal(
    session_factory: SessionFactory,
    *,
    tenant_id: str,
    task_id: str,
) -> bool:
    """Return whether a task has reached a terminal status."""

    with session_factory() as session:
        task = session.scalar(
            select(Task).where(
                Task.tenant_id == tenant_id,
                Task.task_id == task_id,
            )
        )
        if task is None:
            return True
        return TaskStatus(task.status) in _TERMINAL_TASK_STATUSES


def export_task_charter(
    session: Session,
    *,
    tenant_id: str,
    task_id: str,
) -> tuple[bytes, str]:
    """Export the task engineering charter as a zip archive."""

    return export_task_charter_zip(
        session,
        tenant_id=tenant_id,
        task_id=task_id,
    )
