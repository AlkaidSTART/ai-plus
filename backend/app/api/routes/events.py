"""SSE 事件流（api.md §6）：真实 text/event-stream，DB 补发与增量同源。

保留期未确认前不删除事件，过期游标 reset 路径不触发；
超前游标（大于当前最大 seq）按契约返回 422。
"""

import asyncio
import time
import uuid

from fastapi import APIRouter, Depends, Header
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_tenant_id
from app.api.errors import ErrorCode, error_response
from app.db.models import Task, TaskEvent
from app.db.session import get_session
from app.services import events as event_svc
from app.services import tasks as task_svc

router = APIRouter(tags=["insight-events"])

MAX_STREAM_S = 120
POLL_INTERVAL_S = 1.0
HEARTBEAT_IDLE_S = 15.0


@router.get("/insight/task/{task_id}/events")
async def task_events(
    task_id: str,
    after: str = "0",
    last_event_id: str | None = Header(default=None, alias="Last-Event-ID"),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    try:
        tid = uuid.UUID(task_id)
    except ValueError:
        return error_response(422, ErrorCode.INVALID_INPUT, "task_id 必须为 UUID")
    snapshot = await task_svc.get_snapshot(session, tenant_id, tid)
    if snapshot is None:
        return error_response(404, ErrorCode.NOT_FOUND, "任务不存在或不属于当前企业")
    try:
        cursor = event_svc.parse_after(
            last_event_id if last_event_id is not None else after
        )
    except ValueError:
        return error_response(422, ErrorCode.INVALID_EVENT_CURSOR, "非法事件游标")
    if cursor > int(snapshot["last_event_id"]):
        return error_response(422, ErrorCode.INVALID_EVENT_CURSOR, "超前事件游标")
    return StreamingResponse(
        _stream_events(session, tenant_id, tid, cursor),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


async def _stream_state(session, tenant_id, task_id):
    """轻量流状态：任务状态 + 最大 seq（同一事务）。"""
    async with session.begin():
        status = (
            await session.execute(
                select(Task.status).where(
                    Task.id == task_id, Task.tenant_id == tenant_id
                )
            )
        ).scalar_one_or_none()
        if status is None:
            return None
        max_seq = (
            await session.execute(
                select(func.max(TaskEvent.seq)).where(TaskEvent.task_id == task_id)
            )
        ).scalar() or 0
        return status, max_seq


async def _stream_events(session, tenant_id, task_id, cursor):
    yield f"retry: {event_svc.STREAM_RETRY_MS}\n\n"
    last_sent = cursor
    deadline = time.monotonic() + MAX_STREAM_S
    last_activity = time.monotonic()
    while True:
        events = await event_svc.read_events(session, task_id, last_sent)
        for event in events:
            name, eid, data = event_svc.business_event_to_sse(
                str(task_id), event.seq, event.type, event.payload
            )
            last_sent = event.seq
            last_activity = time.monotonic()
            yield event_svc.format_sse(name, data, eid)
        state = await _stream_state(session, tenant_id, task_id)
        if state is None:
            break
        status, max_seq = state
        if status in task_svc.TERMINAL_STATUSES and last_sent >= max_seq:
            yield (
                "event: stream.end\n"
                f"data: {event_svc.stream_end_payload(str(max_seq), status)}\n\n"
            )
            break
        if time.monotonic() - last_activity >= HEARTBEAT_IDLE_S:
            yield event_svc.format_comment()
            last_activity = time.monotonic()
        if time.monotonic() >= deadline:
            break
        await asyncio.sleep(POLL_INTERVAL_S)
