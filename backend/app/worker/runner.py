"""worker 主循环：DB 轮询领取、租约认领、执行、终态聚合。

P0 单 worker、受限 ASIN 并发；Redis 只做可选唤醒，不做必选依赖
（当前无 redis 客户端，纯 DB 轮询；Redis 不可用不影响发现与执行）。
"""

import asyncio
import os
import signal
import socket
from datetime import timedelta

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Task, TaskItem
from app.db.session import SessionFactory
from app.services.tasks import TaskStatus, utcnow
from app.worker import graph as worker_graph

POLL_INTERVAL_S = 2.0
LEASE_TTL_S = 60
CLAIM_BATCH = 10


def worker_id() -> str:
    return f"{socket.gethostname()}:{os.getpid()}"


async def poll_once(
    session: AsyncSession,
    wid: str,
    *,
    make_session=None,
    fixture: dict | None = None,
) -> bool:
    """认领一批 QUEUED 分项并执行；返回是否认领到工作。

    fixture 仅测试/开发入口（生产拒绝由 graph 层执行）。
    """
    make_session = make_session or SessionFactory
    now = utcnow()
    async with session.begin():
        rows = (
            await session.execute(
                select(TaskItem, Task)
                .join(Task, TaskItem.task_id == Task.id)
                .where(
                    TaskItem.status == TaskStatus.QUEUED.value,
                    Task.status.in_(
                        [TaskStatus.QUEUED.value, TaskStatus.RUNNING.value]
                    ),
                    or_(
                        TaskItem.lease_until.is_(None),
                        TaskItem.lease_until < now,
                    ),
                )
                .order_by(Task.created_at, Task.id)
                .limit(CLAIM_BATCH)
                .with_for_update(skip_locked=True)
            )
        ).all()
        claimed = []
        for item, task in rows:
            item.lease_owner = wid
            item.lease_version += 1
            item.lease_until = now + timedelta(seconds=LEASE_TTL_S)
            if item.status == TaskStatus.QUEUED.value:
                item.status = TaskStatus.RUNNING.value
            if task.status == TaskStatus.QUEUED.value:
                task.status = TaskStatus.RUNNING.value
            await session.flush()
            claimed.append(
                (item.id, item.tenant_id, task.id, item.lease_version)
            )
    if not claimed:
        return False
    for item_id, tenant_id, task_id, version in claimed:
        own = make_session()
        try:
            await worker_graph.run_item(
                own,
                tenant_id=tenant_id,
                item_id=item_id,
                worker_id=wid,
                lease_version=version,
                fixture=fixture,
            )
        finally:
            await own.close()
    for task_id in {task for (_, _, task, _) in claimed}:
        tenant_id = next(t for (_, t, task, _) in claimed if task == task_id)
        own = make_session()
        try:
            await worker_graph.finalize_task(
                own, tenant_id=tenant_id, task_id=task_id
            )
        finally:
            await own.close()
    return True


async def main() -> None:
    wid = worker_id()
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    try:
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, stop.set)
    except NotImplementedError:
        pass  # Windows 不支持 add_signal_handler，依赖 KeyboardInterrupt
    while not stop.is_set():
        session = SessionFactory()
        try:
            await poll_once(session, wid)
        finally:
            await session.close()
        await asyncio.sleep(POLL_INTERVAL_S)


if __name__ == "__main__":
    asyncio.run(main())
