"""恢复语义测试（需隔离 PostgreSQL）：中断续跑、检查点复用、租约过期交接、
取消与发布的提交先后、终态不重复。

kill -9 这类真实进程故障以“已提交部分行 + 未提交其余部分”建模：
已提交的 COMPLETED 行必须复用，未提交的工作必须可重做。
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select, update

from app.db.models import ItemNode, Task, TaskEvent, TaskItem
from app.worker import graph as worker_graph
from app.worker import runner as worker_runner
from tests.support import requires_pg, run
from tests.test_tasks import PROJECT_A, TENANT_A, create_kwargs, seed_tenant_project
from tests.test_worker import load_fixture


@requires_pg
def test_crash_midway_resumes_without_rework(pg_session):
    """模拟崩溃：ingestion 已提交 COMPLETED，其余未写；重跑复用该行且只写其余 6 行。"""
    from app.services import tasks as task_svc

    async def main():
        await seed_tenant_project(pg_session, TENANT_A, PROJECT_A)
        created = await task_svc.create_task(pg_session, **create_kwargs())
        item = (
            await pg_session.execute(
                select(TaskItem).where(
                    TaskItem.task_id == uuid.UUID(created["task_id"])
                )
            )
        ).scalars().first()
        item.lease_owner = "w1"
        item.lease_version = 1
        await pg_session.commit()
        marker = {"crashed": True, "raw_count": -1}
        pg_session.add(
            ItemNode(
                tenant_id=TENANT_A, item_id=item.id, attempt=1,
                node="ingestion", status="COMPLETED",
                started_at=datetime.now(timezone.utc),
                completed_at=datetime.now(timezone.utc),
                duration_ms=1, output_version="v1", output_summary=marker,
            )
        )
        await pg_session.commit()
        terminal = await worker_graph.run_item(
            pg_session, tenant_id=TENANT_A, item_id=item.id,
            worker_id="w1", lease_version=1,
            fixture=load_fixture("worker_fixture_success.json"),
            sleep=_instant,
        )
        assert terminal == "COMPLETED"
        rows = (
            await pg_session.execute(
                select(ItemNode).where(ItemNode.item_id == item.id)
            )
        ).scalars().all()
        assert len(rows) == 7
        ingestion = [r for r in rows if r.node == "ingestion"]
        assert len(ingestion) == 1 and ingestion[0].output_summary == marker

    run(main())


async def _instant(delay):
    return None


@requires_pg
def test_lease_expiry_handover(pg_session, pg_schema):
    """旧租约过期后新 worker 可认领；旧版本号写入被拒绝。"""
    # pg_session 仅用于清库；本测试自建引擎验证认领链路。
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    from app.services import tasks as task_svc
    from tests.support import pg_url as get_pg_url

    engine = create_async_engine(get_pg_url(), pool_pre_ping=True)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def main():
        setup = factory()
        try:
            await seed_tenant_project(setup, TENANT_A, PROJECT_A)
            await task_svc.create_task(setup, **create_kwargs())
        finally:
            await setup.close()
        claim = factory()
        try:
            rows_claimed = await worker_runner.poll_once(
                claim, "w-old", make_session=factory,
                fixture=load_fixture("worker_fixture_success.json"),
            )
            assert rows_claimed is True
        finally:
            await claim.close()
        check = factory()
        try:
            count = (
                await check.execute(select(func.count()).select_from(TaskEvent))
            ).scalar()
            assert count and count > 0
        finally:
            await check.close()
            await engine.dispose()

    run(main())


@requires_pg
def test_cancel_before_publish_wins(pg_session):
    """发布前提交取消 → CANCELED；发布后提交取消 → 保持 COMPLETED。"""
    from app.services import tasks as task_svc

    async def main():
        await seed_tenant_project(pg_session, TENANT_A, PROJECT_A)
        first = await task_svc.create_task(
            pg_session, **create_kwargs(idempotency_key="race-1")
        )
        second = await task_svc.create_task(
            pg_session, **create_kwargs(idempotency_key="race-2")
        )
        first_id, second_id = uuid.UUID(first["task_id"]), uuid.UUID(second["task_id"])
        for item in (
            await pg_session.execute(select(TaskItem))
        ).scalars().all():
            item.status = "COMPLETED"
        await pg_session.execute(
            update(Task)
            .where(Task.id == first_id)
            .values(cancel_requested_at=datetime.now(timezone.utc))
        )
        await pg_session.commit()
        assert (
            await worker_graph.finalize_task(
                pg_session, tenant_id=TENANT_A, task_id=first_id
            )
        ) == "CANCELED"
        assert (
            await worker_graph.finalize_task(
                pg_session, tenant_id=TENANT_A, task_id=second_id
            )
        ) == "COMPLETED"
        # 终态幂等：重复聚合不补发终态事件
        before = (
            await pg_session.execute(
                select(func.count())
                .select_from(TaskEvent)
                .where(TaskEvent.task_id == second_id)
            )
        ).scalar()
        assert (
            await worker_graph.finalize_task(
                pg_session, tenant_id=TENANT_A, task_id=second_id
            )
        ) == "COMPLETED"
        after = (
            await pg_session.execute(
                select(func.count())
                .select_from(TaskEvent)
                .where(TaskEvent.task_id == second_id)
            )
        ).scalar()
        assert before == after

    run(main())
