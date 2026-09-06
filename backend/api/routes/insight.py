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
