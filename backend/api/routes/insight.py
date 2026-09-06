"""Insight task routes: create / list / detail / SSE events (docs/api.md §4)."""

import asyncio
import re
import uuid

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse

from api.dependencies import get_app_settings
from api.errors import ApiError, ErrorCode
from api.schemas.common import Envelope
from api.schemas.insight import (
    CreateTasksRequest,
    TaskCreatedItem,
    TaskDetail,
    TaskListData,
    TaskPageData,
    to_task_detail,
)
from core.config import Settings
from runtime.bootstrap import Runtime
from runtime.event_store import TaskEvent
from runtime.task_store import TaskRecord, TaskStatus

router = APIRouter(prefix="/insight", tags=["insight"])

ASIN_RE = re.compile(r"^[A-Z0-9]{10}$")
ASIN_IN_URL_RE = re.compile(r"/dp/([A-Z0-9]{10})")


def get_runtime(request: Request) -> Runtime:
    return request.app.state.runtime


def parse_asins(payload: CreateTasksRequest) -> list[str]:
    asins: list[str] = []
    for asin in payload.asins:
        normalized = asin.strip().upper()
        if not ASIN_RE.fullmatch(normalized):
            raise ApiError(ErrorCode.VALIDATION, f"ASIN 格式不合法: {asin}")
        if normalized not in asins:
            asins.append(normalized)
    if payload.amazon_url:
        match = ASIN_IN_URL_RE.search(payload.amazon_url)
        if not match:
            raise ApiError(ErrorCode.VALIDATION, "无法从 amazon_url 中解析出 ASIN")
        if match.group(1) not in asins:
            asins.append(match.group(1))
    if not asins:
        raise ApiError(ErrorCode.BAD_REQUEST, "asins 与 amazon_url 至少提供一个")
    if not 1 <= len(asins) <= 10:
        raise ApiError(ErrorCode.BAD_REQUEST, "单次任务数量须在 1-10 之间")
    return asins


@router.post("/tasks", response_model=Envelope[TaskListData])
async def create_tasks(
    payload: CreateTasksRequest, runtime: Runtime = Depends(get_runtime)
) -> Envelope[TaskListData]:
    asins = parse_asins(payload)
    created: list[TaskCreatedItem] = []
    for asin in asins:
        record = TaskRecord(
            task_id=f"tsk_{uuid.uuid4().hex[:8]}",
            asin=asin,
            platform=payload.platform,
            marketplace=payload.marketplace,
            review_window_months=payload.review_window_months,
            max_reviews=payload.max_reviews,
            financial_constraint=payload.financial_constraint.model_dump(),
            options=payload.options,
        )
        await runtime.task_store.create(record)
        await runtime.event_store.publish(
            TaskEvent(task_id=record.task_id, step="QUEUED", progress=0, message="任务已入队")
        )
        asyncio.get_running_loop().create_task(runtime.runner.run_task(record.task_id))
        created.append(
            TaskCreatedItem(
                task_id=record.task_id,
                asin=asin,
                status=record.status.value,
                created_at=record.created_at,
            )
        )
    return Envelope(data=TaskListData(tasks=created))


@router.get("/tasks", response_model=Envelope[TaskPageData])
async def list_tasks(
    status: TaskStatus | None = Query(default=None),
    asin: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    runtime: Runtime = Depends(get_runtime),
) -> Envelope[TaskPageData]:
    items, total = await runtime.task_store.list(status, asin, page, page_size)
    return Envelope(
        data=TaskPageData(
            items=[to_task_detail(t) for t in items],
            total=total,
            page=page,
            page_size=page_size,
        )
    )


async def _get_task_or_404(runtime: Runtime, task_id: str) -> TaskRecord:
    task = await runtime.task_store.get(task_id)
    if task is None:
        raise ApiError(ErrorCode.NOT_FOUND, f"任务不存在: {task_id}")
    return task


@router.get("/tasks/{task_id}", response_model=Envelope[TaskDetail])
async def task_detail(
    task_id: str, runtime: Runtime = Depends(get_runtime)
) -> Envelope[TaskDetail]:
    task = await _get_task_or_404(runtime, task_id)
    return Envelope(data=to_task_detail(task))


@router.post("/tasks/{task_id}/cancel", response_model=Envelope[TaskDetail])
async def cancel_task(
    task_id: str, runtime: Runtime = Depends(get_runtime)
) -> Envelope[TaskDetail]:
    task = await _get_task_or_404(runtime, task_id)
    if task.status not in (TaskStatus.PENDING, TaskStatus.RUNNING):
        raise ApiError(
            ErrorCode.CONFLICT, f"任务状态为 {task.status.value}，无法取消"
        )
    runtime.runner.request_cancel(task_id)
    task = await runtime.task_store.update(task_id, status=TaskStatus.CANCELED)
    return Envelope(data=to_task_detail(task))


@router.post("/tasks/{task_id}/retry", response_model=Envelope[TaskDetail])
async def retry_task(
    task_id: str, runtime: Runtime = Depends(get_runtime)
) -> Envelope[TaskDetail]:
    task = await _get_task_or_404(runtime, task_id)
    if task.status != TaskStatus.FAILED:
        raise ApiError(
            ErrorCode.CONFLICT, f"仅 FAILED 任务可重试（当前状态 {task.status.value}）"
        )
    task = await runtime.task_store.update(
        task_id,
        status=TaskStatus.PENDING,
        error_message=None,
        retry_count=0,
        progress=0,
        current_node=None,
        started_at=None,
        finished_at=None,
        final_report=None,
    )
    asyncio.get_running_loop().create_task(runtime.runner.run_task(task_id))
    return Envelope(data=to_task_detail(task))


async def _require_completed_task(runtime: Runtime, task_id: str) -> TaskRecord:
    from services.task_results import require_completed

    task = await _get_task_or_404(runtime, task_id)
    require_completed(task)
    return task


@router.get("/tasks/{task_id}/report")
async def task_report(
    task_id: str, runtime: Runtime = Depends(get_runtime)
) -> Envelope[dict]:
    from services.task_results import clusters_of, evidences_of, financial_of, proposals_of

    task = await _require_completed_task(runtime, task_id)
    return Envelope(
        data={
            "task": to_task_detail(task).model_dump(),
            "clusters": {"items": clusters_of(task)},
            "proposals": {"items": proposals_of(task)},
            "financial": financial_of(task),
            "visual_evidences": {"items": evidences_of(task)},
        }
    )


@router.get("/tasks/{task_id}/clusters")
async def task_clusters(
    task_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=5, ge=1, le=100),
    runtime: Runtime = Depends(get_runtime),
) -> Envelope[dict]:
    from services.task_results import clusters_of

    task = await _require_completed_task(runtime, task_id)
    clusters = clusters_of(task)
    total = len(clusters)
    start = (page - 1) * page_size
    return Envelope(
        data={
            "items": clusters[start : start + page_size],
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    )


@router.get("/tasks/{task_id}/proposals")
async def task_proposals(
    task_id: str,
    track_type: str | None = Query(default=None),
    runtime: Runtime = Depends(get_runtime),
) -> Envelope[dict]:
    from services.task_results import proposals_of

    task = await _require_completed_task(runtime, task_id)
    items = [
        p
        for p in proposals_of(task)
        if track_type is None or p.get("track_type") == track_type
    ]
    return Envelope(data={"items": items, "total": len(items)})


@router.get("/tasks/{task_id}/visual-evidences")
async def task_visual_evidences(
    task_id: str,
    defect_category: str | None = Query(default=None),
    min_confidence: float = Query(default=0.6, ge=0, le=1),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    runtime: Runtime = Depends(get_runtime),
) -> Envelope[dict]:
    from services.task_results import evidences_of

    task = await _require_completed_task(runtime, task_id)
    items = [
        e
        for e in evidences_of(task)
        if (defect_category is None or e.get("defect_category") == defect_category)
        and e.get("confidence", 0) >= min_confidence
    ]
    total = len(items)
    start = (page - 1) * page_size
    return Envelope(
        data={
            "items": items[start : start + page_size],
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    )


SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "X-Accel-Buffering": "no",
    "Connection": "keep-alive",
}
TERMINAL_STEPS = {"COMPLETED", "FAILED", "CANCELED"}


@router.get("/tasks/{task_id}/events")
async def task_events(
    task_id: str,
    runtime: Runtime = Depends(get_runtime),
    settings: Settings = Depends(get_app_settings),
) -> StreamingResponse:
    await _get_task_or_404(runtime, task_id)

    async def event_stream():
        # Reconnect support: replay the most recent events first.
        seen: set[str] = set()
        for event in await runtime.event_store.recent(task_id):
            seen.add(event.id)
            yield event.to_sse()
            if event.step in TERMINAL_STEPS:
                return

        heartbeat = max(settings.SSE_HEARTBEAT_SECONDS, 0.05)
        agen = runtime.event_store.subscribe(task_id)
        try:
            while True:
                try:
                    event = await asyncio.wait_for(anext(agen), timeout=heartbeat)
                except asyncio.TimeoutError:
                    yield ": ping\n\n"
                    continue
                except StopAsyncIteration:
                    break
                if event.id in seen:
                    continue
                seen.add(event.id)
                yield event.to_sse()
                if event.step in TERMINAL_STEPS:
                    break
        finally:
            await agen.aclose()

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )
