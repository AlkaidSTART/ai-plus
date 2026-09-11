"""worker 执行测试：租约、夹具纵切、取消、终态聚合。

DB 部分需隔离 PostgreSQL；纯函数与夹具校验离线可跑。
夹具终态永不写入 reports 表（无假产物断言）。
"""

import json
import os
import uuid

import pytest
from sqlalchemy import func, select, update

from app.db.models import ItemNode, Report, Task, TaskEvent, TaskItem
from app.worker import graph as worker_graph
from app.worker import runner as worker_runner
from tests.support import requires_pg, run
from tests.test_tasks import (
    PROJECT_A,
    TENANT_A,
    create_kwargs,
    seed_tenant_project,
)

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


def load_fixture(name):
    with open(os.path.join(FIXTURES_DIR, name), encoding="utf-8") as fh:
        data = json.load(fh)
    return worker_graph.validate_fixture(data) and data


def test_aggregate_terminal():
    assert worker_graph.aggregate_terminal(["COMPLETED", "FAILED"]) == "COMPLETED"
    assert worker_graph.aggregate_terminal(["FAILED", "CANCELED"]) == "FAILED"
    assert worker_graph.aggregate_terminal(["CANCELED"]) == "CANCELED"


def test_classify_error():
    assert worker_graph.classify_error(TimeoutError()) == "transient"
    assert worker_graph.classify_error(ConnectionError()) == "transient"
    assert worker_graph.classify_error(ValueError()) == "permanent"
    assert worker_graph.classify_error(NotImplementedError()) == "permanent"


def test_backoff_delays():
    assert worker_graph.backoff_delays() == [2, 4, 8]


def test_fixture_files_valid():
    for name in (
        "worker_fixture_success.json",
        "worker_fixture_zero_sample.json",
        "worker_fixture_node_failure.json",
    ):
        data = load_fixture(name)
        assert data["fixture"] is True


def test_fixture_rejects_incomplete(monkeypatch):
    monkeypatch.setattr(worker_graph.settings, "app_env", "prod")
    with pytest.raises(RuntimeError):
        run(
            worker_graph.run_item(
                None,
                tenant_id=TENANT_A,
                item_id=uuid.uuid4(),
                worker_id="w",
                lease_version=1,
                fixture={"fixture": True, "nodes": {}},
            )
        )


def _node_rows(session, item_id):
    async def main():
        result = await session.execute(
            select(ItemNode).where(ItemNode.item_id == item_id)
        )
        return list(result.scalars().all())

    return run(main())


@requires_pg
def test_poll_fixture_success(pg_session, pg_schema):
    # pg_session 仅用于清库；本测试自建引擎验证多连接认领。
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    from tests.support import pg_url as get_pg_url

    engine = create_async_engine(get_pg_url(), pool_pre_ping=True)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def main():
        setup = factory()
        try:
            await seed_tenant_project(setup, TENANT_A, PROJECT_A)
            from app.services import tasks as task_svc

            created = await task_svc.create_task(setup, **create_kwargs())
            task_id = uuid.UUID(created["task_id"])
        finally:
            await setup.close()
        poll_session = factory()
        try:
            claimed = await worker_runner.poll_once(
                poll_session, "w1", make_session=factory,
                fixture=load_fixture("worker_fixture_success.json"),
            )
        finally:
            await poll_session.close()
        assert claimed is True
        check = factory()
        try:
            item = (
                await check.execute(
                    select(TaskItem).where(TaskItem.task_id == task_id)
                )
            ).scalars().first()
            assert item.status == "COMPLETED"
            rows = (
                await check.execute(
                    select(ItemNode).where(ItemNode.item_id == item.id)
                )
            ).scalars().all()
            assert len(rows) == 7
            assert {r.status for r in rows} == {"COMPLETED"}
            seqs = (
                await check.execute(
                    select(TaskEvent.seq)
                    .where(TaskEvent.task_id == task_id)
                    .order_by(TaskEvent.seq)
                )
            ).scalars().all()
            assert seqs == sorted(seqs) and len(seqs) >= 9
            assert (
                await check.execute(select(func.count()).select_from(Report))
            ).scalar() == 0
            task = (
                await check.execute(select(Task).where(Task.id == task_id))
            ).scalar_one()
            assert task.status == "COMPLETED"
        finally:
            await check.close()
            await engine.dispose()

    run(main())


@requires_pg
def test_fixture_zero_sample_and_failure(pg_session):
    from app.services import tasks as task_svc

    async def main():
        await seed_tenant_project(pg_session, TENANT_A, PROJECT_A)
        zero = await task_svc.create_task(
            pg_session, **create_kwargs(idempotency_key="zero")
        )
        failed = await task_svc.create_task(
            pg_session, **create_kwargs(idempotency_key="fail")
        )
        for task_id, fixture_name, expected in (
            (zero["task_id"], "worker_fixture_zero_sample.json", "COMPLETED"),
            (failed["task_id"], "worker_fixture_node_failure.json", "FAILED"),
        ):
            tid = uuid.UUID(task_id)
            item = (
                await pg_session.execute(
                    select(TaskItem).where(TaskItem.task_id == tid)
                )
            ).scalars().first()
            item.lease_owner = "w1"
            item.lease_version = 1
            await pg_session.commit()
            terminal = await worker_graph.run_item(
                pg_session, tenant_id=TENANT_A, item_id=item.id,
                worker_id="w1", lease_version=1,
                fixture=load_fixture(fixture_name), sleep=_no_sleep,
            )
            assert terminal == expected
            await worker_graph.finalize_task(
                pg_session, tenant_id=TENANT_A, task_id=tid
            )
        rows = (
            await pg_session.execute(select(ItemNode))
        ).scalars().all()
        assert {r.status for r in rows} <= {"COMPLETED", "SKIPPED", "FAILED"}

    run(main())


async def _no_sleep(delay):
    return None


@requires_pg
def test_stale_lease_rejected(pg_session):
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
        item.lease_owner = "w-other"
        item.lease_version = 9
        await pg_session.commit()
        result = await worker_graph.run_item(
            pg_session, tenant_id=TENANT_A, item_id=item.id,
            worker_id="w1", lease_version=4,
            fixture=load_fixture("worker_fixture_success.json"),
            sleep=_no_sleep,
        )
        assert result == "STOLEN"
        assert (
            await pg_session.execute(
                select(func.count()).select_from(ItemNode)
            )
        ).scalar() == 0

    run(main())


@requires_pg
def test_preset_cancel_marks_canceled(pg_session):
    from datetime import datetime, timezone

    from app.services import tasks as task_svc

    async def main():
        await seed_tenant_project(pg_session, TENANT_A, PROJECT_A)
        created = await task_svc.create_task(pg_session, **create_kwargs())
        task_id = uuid.UUID(created["task_id"])
        await pg_session.execute(
            update(Task)
            .where(Task.id == task_id)
            .values(cancel_requested_at=datetime.now(timezone.utc))
        )
        await pg_session.commit()
        item = (
            await pg_session.execute(
                select(TaskItem).where(TaskItem.task_id == task_id)
            )
        ).scalars().first()
        item.lease_owner = "w1"
        item.lease_version = 1
        await pg_session.commit()
        terminal = await worker_graph.run_item(
            pg_session, tenant_id=TENANT_A, item_id=item.id,
            worker_id="w1", lease_version=1,
            fixture=load_fixture("worker_fixture_success.json"),
            sleep=_no_sleep,
        )
        assert terminal == "CANCELED"
        rows = (
            await pg_session.execute(
                select(ItemNode).where(ItemNode.item_id == item.id)
            )
        ).scalars().all()
        by_node = {r.node: r.status for r in rows}
        assert by_node["ingestion"] == "CANCELED"
        assert set(by_node.values()) == {"CANCELED", "SKIPPED"}
        assert len(by_node) == 7

    run(main())
