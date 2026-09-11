"""任务持久化测试（需隔离 PostgreSQL；无库时 DB 部分整文件跳过）。

并发与隔离语义只在真实库验证，不用 SQLite 代替。
"""

import asyncio
import uuid
from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy import select, update

from app.api.deps import get_current_tenant_id
from app.db.models import Project, Task, TaskItem, Tenant
from app.db.session import get_session
from app.main import create_app
from app.services import tasks as task_svc
from tests.support import requires_pg, run

TODAY = date(2026, 9, 10)
TENANT_A = uuid.uuid5(uuid.NAMESPACE_URL, "test03/tenant-a")
PROJECT_A = uuid.uuid5(uuid.NAMESPACE_URL, "test03/project-a")
TENANT_B = uuid.uuid5(uuid.NAMESPACE_URL, "test03/tenant-b")
PROJECT_B = uuid.uuid5(uuid.NAMESPACE_URL, "test03/project-b")


async def seed_tenant_project(session, tenant_id, project_id, marketplace="US"):
    session.add(Tenant(id=tenant_id, name="t"))
    session.add(
        Project(id=project_id, tenant_id=tenant_id, name="p", marketplace=marketplace)
    )
    await session.commit()


async def force_terminal_failed(session, task_id):
    await session.execute(
        update(Task).where(Task.id == task_id).values(status="FAILED")
    )
    await session.execute(
        update(TaskItem).where(TaskItem.task_id == task_id).values(status="FAILED")
    )
    await session.commit()


def make_client(pg_session, tenant_id):
    app = create_app()

    async def override_session():
        yield pg_session

    async def override_tenant():
        return tenant_id

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_current_tenant_id] = override_tenant
    return TestClient(app)


def create_kwargs(**overrides):
    params = {
        "tenant_id": TENANT_A,
        "project_id": PROJECT_A,
        "platform": "amazon",
        "marketplace": "US",
        "asins": ["B012345678", "b087654321"],
        "window_given": None,
        "idempotency_key": "k1",
        "today": TODAY,
    }
    params.update(overrides)
    return params


@requires_pg
def test_create_and_snapshot(pg_session):
    async def main():
        await seed_tenant_project(pg_session, TENANT_A, PROJECT_A)
        created = await task_svc.create_task(pg_session, **create_kwargs())
        assert created["reused"] is False
        assert [i["asin"] for i in created["items"]] == ["B012345678", "B087654321"]
        assert created["window"] == {
            "start_date": "2026-03-10",
            "end_date": "2026-09-10",
        }
        assert created["links"]["events"].endswith("/events")
        snap = await task_svc.get_snapshot(
            pg_session, TENANT_A, uuid.UUID(created["task_id"])
        )
        assert snap["last_event_id"] == "1"
        assert snap["item_counts"] == {
            "total": 2,
            "queued": 2,
            "running": 0,
            "completed": 0,
            "failed": 0,
            "canceled": 0,
        }
        assert all(
            item["report_id"] is None and item["nodes"] == [] for item in snap["items"]
        )
        assert snap["warnings"] == []

    run(main())


@requires_pg
def test_idempotent_replay_returns_original(pg_session):
    async def main():
        await seed_tenant_project(pg_session, TENANT_A, PROJECT_A)
        first = await task_svc.create_task(pg_session, **create_kwargs())
        second = await task_svc.create_task(pg_session, **create_kwargs())
        assert second["reused"] is True
        assert second["task_id"] == first["task_id"]
        count = await pg_session.execute(
            select(task_svc.func.count()).select_from(Task)
        )
        assert count.scalar() == 1

    run(main())


@requires_pg
def test_same_key_different_input_conflicts(pg_session):
    async def main():
        await seed_tenant_project(pg_session, TENANT_A, PROJECT_A)
        await task_svc.create_task(pg_session, **create_kwargs())
        try:
            await task_svc.create_task(
                pg_session, **create_kwargs(asins=["B099999999"])
            )
        except task_svc.IdempotencyConflict:
            return
        raise AssertionError("同键不同输入应冲突")

    run(main())


@requires_pg
def test_concurrent_same_key_single_task(pg_session, pg_schema):
    """两连接并发同键创建：恰好一个 reused=False，同一 task_id。"""
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    from tests.support import pg_url as get_pg_url

    async def main():
        await seed_tenant_project(pg_session, TENANT_A, PROJECT_A)
        engine = create_async_engine(get_pg_url(), pool_pre_ping=True)
        factory = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        session_b = factory()
        try:
            results = await asyncio.gather(
                task_svc.create_task(pg_session, **create_kwargs()),
                task_svc.create_task(session_b, **create_kwargs()),
            )
        finally:
            await session_b.close()
            await engine.dispose()
        assert {r["reused"] for r in results} == {True, False}
        assert results[0]["task_id"] == results[1]["task_id"]

    run(main())


@requires_pg
def test_list_pagination_and_cursor_binding(pg_session):
    async def main():
        await seed_tenant_project(pg_session, TENANT_A, PROJECT_A)
        for key in ("k1", "k2", "k3"):
            await task_svc.create_task(
                pg_session, **create_kwargs(idempotency_key=key)
            )
        page1, cursor = await task_svc.list_tasks(
            pg_session, tenant_id=TENANT_A, project_id=None, status=None,
            cursor=None, limit=2,
        )
        assert len(page1) == 2 and cursor is not None
        page2, cursor2 = await task_svc.list_tasks(
            pg_session, tenant_id=TENANT_A, project_id=None, status=None,
            cursor=cursor, limit=2,
        )
        assert len(page2) == 1 and cursor2 is None
        assert {i["task_id"] for i in page1} != {i["task_id"] for i in page2}
        try:
            await task_svc.list_tasks(
                pg_session, tenant_id=TENANT_A, project_id=PROJECT_A, status=None,
                cursor=cursor, limit=2,
            )
        except ValueError:
            return
        raise AssertionError("跨过滤条件的游标应拒绝")

    run(main())


@requires_pg
def test_cancel_first_wins_and_terminal_returns_original(pg_session):
    async def main():
        await seed_tenant_project(pg_session, TENANT_A, PROJECT_A)
        created = await task_svc.create_task(pg_session, **create_kwargs())
        task_id = uuid.UUID(created["task_id"])
        first = await task_svc.cancel_task(pg_session, TENANT_A, task_id)
        second = await task_svc.cancel_task(pg_session, TENANT_A, task_id)
        assert first["cancel_requested_at"] is not None
        assert second["cancel_requested_at"] == first["cancel_requested_at"]
        await force_terminal_failed(pg_session, task_id)
        terminal = await task_svc.cancel_task(pg_session, TENANT_A, task_id)
        assert terminal["status"] == "FAILED"

    run(main())


@requires_pg
def test_retry_failed_items_new_task(pg_session):
    async def main():
        await seed_tenant_project(pg_session, TENANT_A, PROJECT_A)
        created = await task_svc.create_task(pg_session, **create_kwargs())
        task_id = uuid.UUID(created["task_id"])
        await force_terminal_failed(pg_session, task_id)
        failed_ids = [i["item_id"] for i in created["items"][:1]]
        retried = await task_svc.retry_task(
            pg_session, tenant_id=TENANT_A, source_task_id=task_id,
            item_ids=failed_ids, idempotency_key="retry-1",
        )
        assert retried["parent_task_id"] == str(task_id)
        assert retried["task_id"] != str(task_id)
        assert [i["asin"] for i in retried["items"]] == [
            created["items"][0]["asin"]
        ]
        try:
            await task_svc.retry_task(
                pg_session, tenant_id=TENANT_A, source_task_id=task_id,
                item_ids=[], idempotency_key="retry-2",
            )
        except task_svc.NotRetryable:
            return
        raise AssertionError("空分项重试应拒绝")

    run(main())


@requires_pg
def test_routes_create_cancel_retry_flow(pg_session):
    async def main():
        await seed_tenant_project(pg_session, TENANT_A, PROJECT_A)

    run(main())
    client = make_client(pg_session, TENANT_A)
    created = client.post(
        "/api/v1/insight/task",
        headers={"Idempotency-Key": "route-k1"},
        json={"project_id": str(PROJECT_A), "asins": ["B012345678"]},
    )
    assert created.status_code == 202, created.text
    body = created.json()
    assert body["reused"] is False
    assert created.headers.get("X-Request-ID", "").startswith("req_")
    task_id = body["task_id"]

    missing_key = client.post(
        "/api/v1/insight/task",
        json={"project_id": str(PROJECT_A), "asins": ["B012345678"]},
    )
    assert missing_key.status_code == 422
    assert missing_key.json()["error"]["code"] == "INVALID_INPUT"

    bad_project = client.post(
        "/api/v1/insight/task",
        headers={"Idempotency-Key": "route-k2"},
        json={"project_id": str(uuid.uuid4()), "asins": ["B012345678"]},
    )
    assert bad_project.status_code == 404

    snapshot = client.get(f"/api/v1/insight/task/{task_id}")
    assert snapshot.status_code == 200
    assert snapshot.json()["last_event_id"] == "1"

    canceled = client.post(f"/api/v1/insight/task/{task_id}/cancel")
    assert canceled.status_code == 202
    assert canceled.json()["cancel_requested_at"] is not None

    async def fail_all():
        await force_terminal_failed(pg_session, uuid.UUID(task_id))

    run(fail_all())
    item_id = body["items"][0]["item_id"]
    retried = client.post(
        f"/api/v1/insight/task/{task_id}/retry",
        headers={"Idempotency-Key": "route-retry-1"},
        json={"item_ids": [item_id]},
    )
    assert retried.status_code == 202, retried.text
    assert retried.json()["parent_task_id"] == task_id

    retry_active = client.post(
        f"/api/v1/insight/task/{retried.json()['task_id']}/retry",
        headers={"Idempotency-Key": "route-retry-2"},
        json={"item_ids": [item_id]},
    )
    assert retry_active.status_code == 409
    assert retry_active.json()["error"]["code"] == "ITEM_NOT_RETRYABLE"


@requires_pg
def test_routes_malformed_ids_rejected(pg_session):
    client = make_client(pg_session, TENANT_A)
    assert client.get("/api/v1/insight/task/not-a-uuid").status_code == 422
    assert client.post("/api/v1/insight/task/not-a-uuid/cancel").status_code == 422
