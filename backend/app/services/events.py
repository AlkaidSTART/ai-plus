"""任务事件服务：seq 分配、读取、SSE 格式化。

seq 分配在同一事务内锁定任务行后取 max+1，禁止裸 max+1 并发写入。
保留期未确认前不删除事件，因此过期游标 reset 路径暂不触发（已记录）。
"""

import json
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Task, TaskEvent

SCHEMA_VERSION = 1
STREAM_RETRY_MS = 3000
HEARTBEAT_COMMENT = "heartbeat"


def format_sse(
    event: str | None, data: str, event_id: str | None = None, retry: int | None = None
) -> str:
    lines = []
    if retry is not None:
        lines.append(f"retry: {retry}")
    if event_id is not None:
        lines.append(f"id: {event_id}")
    if event is not None:
        lines.append(f"event: {event}")
    for data_line in data.splitlines() or [""]:
        lines.append(f"data: {data_line}")
    lines.append("")
    lines.append("")
    return "\n".join(lines)


def format_comment(text: str = HEARTBEAT_COMMENT) -> str:
    return f": {text}\n\n"


def parse_after(value: str) -> int:
    """游标必须为非负整数；非法抛 ValueError（路由转为 422）。"""
    try:
        after = int(value)
    except (ValueError, TypeError) as exc:
        raise ValueError("非法事件游标") from exc
    if after < 0:
        raise ValueError("非法事件游标")
    return after


def business_event_to_sse(
    task_id: str, seq: int, event_type: str, payload: dict
) -> tuple[str, str, str]:
    """业务事件转 SSE 三元组（事件名、id、data），字段见 api.md §6.1。"""
    data = json.dumps(
        {
            "schema_version": SCHEMA_VERSION,
            "task_id": task_id,
            "seq": seq,
            "item_id": payload.get("item_id"),
            "attempt": payload.get("attempt"),
            "occurred_at": payload.get("occurred_at"),
            "payload": payload.get("payload", {}),
        },
        ensure_ascii=False,
    )
    return event_type, str(seq), data


def stream_end_payload(last_event_id: str, status: str) -> str:
    return json.dumps(
        {"last_event_id": last_event_id, "status": status}, ensure_ascii=False
    )


async def append_event(
    session: AsyncSession,
    *,
    tenant_id,
    task_id,
    event_type: str,
    payload: dict,
    item_id=None,
    attempt: int | None = None,
    occurred_at: datetime | None = None,
) -> int:
    """追加事件并返回 seq。调用方须在已有事务内或由本函数建事务？

    本函数自己管理事务：锁定任务行 → 取 max(seq) → 插入提交。
    """
    from app.services.tasks import utcnow

    async with session.begin():
        task = (
            await session.execute(
                select(Task)
                .where(Task.id == task_id, Task.tenant_id == tenant_id)
                .with_for_update()
            )
        ).scalar_one_or_none()
        if task is None:
            raise ValueError("任务不存在或不属于当前企业")
        max_seq = (
            await session.execute(
                select(func.max(TaskEvent.seq)).where(TaskEvent.task_id == task_id)
            )
        ).scalar() or 0
        occurred = occurred_at or utcnow()
        session.add(
            TaskEvent(
                tenant_id=tenant_id,
                task_id=task_id,
                seq=max_seq + 1,
                type=event_type,
                item_id=item_id,
                attempt=attempt,
                occurred_at=occurred,
                payload={
                    **payload,
                    "item_id": str(item_id) if item_id is not None else None,
                    "attempt": attempt,
                    "occurred_at": occurred.isoformat(),
                },
            )
        )
        await session.flush()
        return max_seq + 1


async def read_events(
    session: AsyncSession, task_id, after: int, limit: int = 500
) -> list[TaskEvent]:
    """按 seq 增量读取；补发与实时订阅的共同来源。"""
    async with session.begin():
        result = await session.execute(
            select(TaskEvent)
            .where(TaskEvent.task_id == task_id, TaskEvent.seq > after)
            .order_by(TaskEvent.seq)
            .limit(limit)
        )
        return list(result.scalars().all())
