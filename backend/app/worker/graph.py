"""分项执行图（阶段 04）：租约守卫、取消协作、重试分类、终态聚合。

fixture 仅测试/开发入口，生产拒绝；fixture 之外走真实 run_node，
现阶段节点未实现则走明确失败路径，不返回假成功。
恢复语义：已提交的 COMPLETED 节点行直接复用，不重新执行、不补发事件；
同一节点的新版本行只在恢复继续时写入。
LangGraph 图绑定待依赖可用后接入：本文件即执行语义的事实来源，
后续绑定不得改变这里的租约/取消/幂等/终态规则。
"""

import asyncio
import uuid

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.models import ItemNode, Task, TaskItem
from app.services import events as event_svc
from app.services.tasks import TERMINAL_STATUSES, TaskStatus, utcnow
from app.worker.nodes import NODE_ORDER, run_node

MAX_NODE_RETRIES = 3  # 瞬时错误最多重试 3 次（首次 + 3 次 = 4 次尝试）
BACKOFF_DELAYS = [2, 4, 8]


class LeaseLost(Exception):
    """租约已易主：静默中止，不写任何产物。"""


def classify_error(exc: Exception) -> str:
    """瞬时错误可重试，永久错误（含节点未实现）直接失败。"""
    if isinstance(exc, (TimeoutError, ConnectionError)):
        return "transient"
    return "permanent"


def backoff_delays() -> list[int]:
    return list(BACKOFF_DELAYS)


def aggregate_terminal(statuses: list[str]) -> str:
    """纯终态聚合（调用方保证非空且全为终态）。

    有 COMPLETED 则 COMPLETED；否则有 FAILED 则 FAILED；否则 CANCELED。
    07 会在此基础上叠加“已发布报告”口径，本函数只看分项终态。
    """
    values = set(statuses)
    if TaskStatus.COMPLETED.value in values:
        return TaskStatus.COMPLETED.value
    if TaskStatus.FAILED.value in values:
        return TaskStatus.FAILED.value
    return TaskStatus.CANCELED.value


def validate_fixture(fixture: dict) -> dict:
    if not isinstance(fixture, dict) or fixture.get("fixture") is not True:
        raise ValueError("测试夹具必须显式标记 fixture: true")
    nodes = fixture.get("nodes", {})
    if set(nodes) != set(NODE_ORDER):
        raise ValueError("夹具必须定义全部 7 个节点")
    for name, outcome in nodes.items():
        if outcome.get("status") not in ("completed", "failed", "skipped"):
            raise ValueError(f"夹具节点状态非法：{name}")
    return nodes


async def _cancel_requested(
    session: AsyncSession, tenant_id: uuid.UUID, task_id: uuid.UUID
):
    async with session.begin():
        result = await session.execute(
            select(Task.cancel_requested_at).where(
                Task.id == task_id, Task.tenant_id == tenant_id
            )
        )
        return result.scalar_one_or_none()


async def _lease_ok(
    session: AsyncSession, item_id: uuid.UUID, worker_id: str, lease_version: int
) -> bool:
    async with session.begin():
        result = await session.execute(
            select(TaskItem.lease_owner, TaskItem.lease_version).where(
                TaskItem.id == item_id
            )
        )
        row = result.one_or_none()
        return row is not None and tuple(row) == (worker_id, lease_version)


async def _existing_versions(
    session: AsyncSession, item_id: uuid.UUID, attempt: int, node: str
) -> list[ItemNode]:
    async with session.begin():
        result = await session.execute(
            select(ItemNode)
            .where(
                ItemNode.item_id == item_id,
                ItemNode.attempt == attempt,
                ItemNode.node == node,
            )
            .order_by(ItemNode.output_version)
        )
        return list(result.scalars().all())


async def _write_node_row(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    item_id: uuid.UUID,
    attempt: int,
    node: str,
    status: str,
    started_at,
    completed_at,
    duration_ms: int | None,
    output_version: str,
    output_summary: dict | None,
    skip_reason: str | None,
) -> tuple[ItemNode, bool]:
    """写节点行；版本冲突则复用胜出者（恢复/竞态路径），返回 (row, inserted)。"""
    async with session.begin():
        row = ItemNode(
            tenant_id=tenant_id,
            item_id=item_id,
            attempt=attempt,
            node=node,
            status=status,
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=duration_ms,
            output_version=output_version,
            output_summary=output_summary,
            skip_reason=skip_reason,
        )
        session.add(row)
        try:
            await session.flush()
        except IntegrityError:
            pass
        else:
            await session.execute(
                update(TaskItem)
                .where(TaskItem.id == item_id)
                .values(current_node=node)
            )
            await session.flush()
            return row, True
        result = await session.execute(
            select(ItemNode).where(
                ItemNode.item_id == item_id,
                ItemNode.attempt == attempt,
                ItemNode.node == node,
                ItemNode.output_version == output_version,
            )
        )
        return result.scalar_one(), False


async def _emit_node_event(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    task_id: uuid.UUID,
    item_id: uuid.UUID,
    attempt: int,
    node: str,
    status: str,
    duration_ms: int | None,
    skip_reason: str | None,
) -> None:
    await event_svc.append_event(
        session,
        tenant_id=tenant_id,
        task_id=task_id,
        event_type="node.updated",
        payload={
            "node": node,
            "status": status,
            "duration_ms": duration_ms,
            "skip_reason": skip_reason,
        },
        item_id=item_id,
        attempt=attempt,
    )


async def _execute_node_real(node: str, item_id: uuid.UUID, attempt: int) -> dict | None:
    """真实节点执行。现阶段实现抛 NotImplementedError，上层按永久失败处理。"""
    await run_node(node, str(item_id), attempt)
    return None


async def run_item(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    item_id: uuid.UUID,
    worker_id: str,
    lease_version: int,
    fixture: dict | None = None,
    sleep=asyncio.sleep,
) -> str:
    """执行单个分项，返回终态（COMPLETED/FAILED/CANCELED）或 "STOLEN"（租约丢失）。

    fixture 为 None 时走真实 run_node；恢复时复用已提交的 COMPLETED 产物。
    """
    if fixture is not None:
        if settings.app_env == "prod":
            raise RuntimeError("生产环境拒绝测试夹具")
        node_outcomes = validate_fixture(fixture)
    else:
        node_outcomes = {}

    async with session.begin():
        item = (
            await session.execute(
                select(TaskItem).where(
                    TaskItem.id == item_id, TaskItem.tenant_id == tenant_id
                )
            )
        ).scalar_one_or_none()
        if item is None:
            raise ValueError("分项不存在或不属于当前企业")
        task_id, attempt = item.task_id, item.attempt

    for index, node in enumerate(NODE_ORDER):
        if await _cancel_requested(session, tenant_id, task_id):
            await _finalize_cancel(
                session,
                tenant_id=tenant_id,
                task_id=task_id,
                item_id=item_id,
                attempt=attempt,
                node_index=index,
            )
            return TaskStatus.CANCELED.value
        if not await _lease_ok(session, item_id, worker_id, lease_version):
            return "STOLEN"

        existing = await _existing_versions(session, item_id, attempt, node)
        if any(r.status == TaskStatus.COMPLETED.value for r in existing):
            continue  # 恢复：复用已提交产物，不重新执行、不补发事件

        outcome = node_outcomes.get(node)
        if outcome is not None and outcome["status"] == "skipped":
            row, inserted = await _write_node_row(
                session,
                tenant_id=tenant_id,
                item_id=item_id,
                attempt=attempt,
                node=node,
                status=TaskStatus.SKIPPED.value,
                started_at=None,
                completed_at=utcnow(),
                duration_ms=outcome.get("duration_ms"),
                output_version="v1",
                output_summary=None,
                skip_reason=outcome.get("skip_reason"),
            )
            if inserted:
                await _emit_node_event(
                    session,
                    tenant_id=tenant_id,
                    task_id=task_id,
                    item_id=item_id,
                    attempt=attempt,
                    node=node,
                    status=row.status,
                    duration_ms=row.duration_ms,
                    skip_reason=row.skip_reason,
                )
            continue

        # completed / failed / 真实执行：内存中重试，只落最终版本行
        version = f"v{len(existing) + 1}"
        outcome_status = TaskStatus.FAILED.value
        summary: dict | None = None
        duration_ms: int | None = None
        error_text: str | None = None
        for try_index in range(1, MAX_NODE_RETRIES + 2):
            started = utcnow()
            kind = "permanent"
            error_text = None
            try:
                if outcome is not None:
                    if outcome["status"] == "completed":
                        summary = outcome.get("output_summary")
                        outcome_status = TaskStatus.COMPLETED.value
                    else:
                        kind = outcome.get("error_kind", "permanent")
                        error_text = outcome.get("error", "fixture failure")
                        raise RuntimeError(error_text)
                else:
                    summary = await _execute_node_real(node, item_id, attempt)
                    outcome_status = TaskStatus.COMPLETED.value
            except Exception as exc:  # noqa: BLE001 — 分类后记录
                if outcome is None:
                    kind = classify_error(exc)
                error_text = error_text or str(exc)
            ended = utcnow()
            duration_ms = int((ended - started).total_seconds() * 1000)
            if outcome_status == TaskStatus.COMPLETED.value or kind != "transient":
                break
            if try_index <= MAX_NODE_RETRIES:
                await sleep(backoff_delays()[try_index - 1])

        row, inserted = await _write_node_row(
            session,
            tenant_id=tenant_id,
            item_id=item_id,
            attempt=attempt,
            node=node,
            status=outcome_status,
            started_at=started,
            completed_at=ended,
            duration_ms=duration_ms,
            output_version=version,
            output_summary=summary,
            skip_reason=None,
        )
        if inserted:
            await _emit_node_event(
                session,
                tenant_id=tenant_id,
                task_id=task_id,
                item_id=item_id,
                attempt=attempt,
                node=node,
                status=row.status,
                duration_ms=row.duration_ms,
                skip_reason=None,
            )
        if row.status != TaskStatus.COMPLETED.value:
            await _finalize_item_failed(
                session,
                tenant_id=tenant_id,
                task_id=task_id,
                item_id=item_id,
                attempt=attempt,
                node_index=index,
                error=error_text or "节点执行失败",
            )
            return TaskStatus.FAILED.value

    if await _cancel_requested(session, tenant_id, task_id):
        await _finalize_cancel(
            session,
            tenant_id=tenant_id,
            task_id=task_id,
            item_id=item_id,
            attempt=attempt,
            node_index=len(NODE_ORDER),
        )
        return TaskStatus.CANCELED.value
    async with session.begin():
        item = (
            await session.execute(select(TaskItem).where(TaskItem.id == item_id))
        ).scalar_one()
        item.status = TaskStatus.COMPLETED.value
        item.current_node = None
        await session.flush()
    await event_svc.append_event(
        session,
        tenant_id=tenant_id,
        task_id=task_id,
        event_type="item.updated",
        payload={"status": TaskStatus.COMPLETED.value},
        item_id=item_id,
        attempt=attempt,
    )
    return TaskStatus.COMPLETED.value


async def _finalize_item_failed(
    session, *, tenant_id, task_id, item_id, attempt, node_index, error
) -> None:
    for rest in NODE_ORDER[node_index + 1 :]:
        row, inserted = await _write_node_row(
            session,
            tenant_id=tenant_id,
            item_id=item_id,
            attempt=attempt,
            node=rest,
            status=TaskStatus.SKIPPED.value,
            started_at=None,
            completed_at=utcnow(),
            duration_ms=None,
            output_version="v1",
            output_summary=None,
            skip_reason="CASCADE",
        )
        if inserted:
            await _emit_node_event(
                session,
                tenant_id=tenant_id,
                task_id=task_id,
                item_id=item_id,
                attempt=attempt,
                node=rest,
                status=TaskStatus.SKIPPED.value,
                duration_ms=None,
                skip_reason="CASCADE",
            )
    async with session.begin():
        item = (
            await session.execute(select(TaskItem).where(TaskItem.id == item_id))
        ).scalar_one()
        item.status = TaskStatus.FAILED.value
        item.current_node = None
        item.error = {"code": "NODE_FAILED", "message": error, "retryable": True}
        await session.flush()
    await event_svc.append_event(
        session,
        tenant_id=tenant_id,
        task_id=task_id,
        event_type="item.updated",
        payload={"status": TaskStatus.FAILED.value, "error": error},
        item_id=item_id,
        attempt=attempt,
    )


async def _finalize_cancel(
    session, *, tenant_id, task_id, item_id, attempt, node_index
) -> None:
    for position, rest in enumerate(NODE_ORDER[node_index:]):
        status = (
            TaskStatus.CANCELED.value if position == 0 else TaskStatus.SKIPPED.value
        )
        row, inserted = await _write_node_row(
            session,
            tenant_id=tenant_id,
            item_id=item_id,
            attempt=attempt,
            node=rest,
            status=status,
            started_at=None,
            completed_at=utcnow(),
            duration_ms=None,
            output_version="v1",
            output_summary=None,
            skip_reason="CANCELED",
        )
        if inserted:
            await _emit_node_event(
                session,
                tenant_id=tenant_id,
                task_id=task_id,
                item_id=item_id,
                attempt=attempt,
                node=rest,
                status=status,
                duration_ms=None,
                skip_reason="CANCELED",
            )
    async with session.begin():
        item = (
            await session.execute(select(TaskItem).where(TaskItem.id == item_id))
        ).scalar_one()
        item.status = TaskStatus.CANCELED.value
        item.current_node = None
        await session.flush()
    await event_svc.append_event(
        session,
        tenant_id=tenant_id,
        task_id=task_id,
        event_type="item.updated",
        payload={"status": TaskStatus.CANCELED.value},
        item_id=item_id,
        attempt=attempt,
    )


async def finalize_task(
    session: AsyncSession, *, tenant_id: uuid.UUID, task_id: uuid.UUID
) -> str:
    """聚合任务终态。已终结则直接返回（不补发终态事件）；取消优先于完成。"""
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
        if task.status in TERMINAL_STATUSES:
            return task.status
        items = (
            await session.execute(
                select(TaskItem).where(TaskItem.task_id == task_id)
            )
        ).scalars().all()
        if task.cancel_requested_at is not None:
            terminal = TaskStatus.CANCELED.value
        else:
            terminal = aggregate_terminal([item.status for item in items])
        task.status = terminal
        task.completed_at = utcnow()
        await session.flush()
        counts: dict[str, int] = {"total": len(items)}
        for item in items:
            key = item.status.lower()
            counts[key] = counts.get(key, 0) + 1
    event_type = {
        TaskStatus.COMPLETED.value: "task.completed",
        TaskStatus.FAILED.value: "task.failed",
        TaskStatus.CANCELED.value: "task.canceled",
    }[terminal]
    await event_svc.append_event(
        session,
        tenant_id=tenant_id,
        task_id=task_id,
        event_type=event_type,
        payload={"status": terminal, "item_counts": counts},
    )
    return terminal
