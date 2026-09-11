"""租户隔离测试：越权 404、请求头不可伪造身份、生产禁用预置。

DB 部分需隔离 PostgreSQL；生产拒绝测试离线可跑。
"""

import uuid

import pytest
from fastapi import HTTPException

from app.api import deps
from app.services import tasks as task_svc
from tests.support import requires_pg, run
from tests.test_tasks import TENANT_A, TENANT_B, make_client, seed_tenant_project
from tests.test_tasks import PROJECT_A
from tests.test_tasks import PROJECT_B


def test_prod_refuses_preset_identity(monkeypatch):
    monkeypatch.setattr(deps.settings, "app_env", "prod")
    with pytest.raises(HTTPException) as exc_info:
        run(deps.get_current_tenant_id())
    assert exc_info.value.status_code == 401


@requires_pg
def test_cross_tenant_snapshot_invisible(pg_session):
    async def main():
        await seed_tenant_project(pg_session, TENANT_A, PROJECT_A)
        from tests.test_tasks import create_kwargs

        created = await task_svc.create_task(pg_session, **create_kwargs())
        assert (
            await task_svc.get_snapshot(
                pg_session, TENANT_B, uuid.UUID(created["task_id"])
            )
            is None
        )

    run(main())


@requires_pg
def test_forged_project_rejected(pg_session):
    async def main():
        await seed_tenant_project(pg_session, TENANT_A, PROJECT_A)
        await seed_tenant_project(pg_session, TENANT_B, PROJECT_B)
        from tests.test_tasks import create_kwargs

        try:
            await task_svc.create_task(
                pg_session, **create_kwargs(project_id=PROJECT_B)
            )
        except task_svc.ProjectNotFound:
            return
        raise AssertionError("他租户项目应拒绝")

    run(main())


@requires_pg
def test_request_header_cannot_forge_tenant(pg_session):
    async def main():
        await seed_tenant_project(pg_session, TENANT_A, PROJECT_A)

    run(main())
    client = make_client(pg_session, TENANT_A)
    evil = str(uuid.uuid4())
    resp = client.post(
        "/api/v1/insight/task",
        headers={"Idempotency-Key": "iso-k1", "X-Tenant-ID": evil},
        json={"project_id": str(PROJECT_A), "asins": ["B012345678"]},
    )
    assert resp.status_code == 202, resp.text

    async def check_owner():
        from sqlalchemy import select

        from app.db.models import Task

        task = (
            await pg_session.execute(
                select(Task).where(Task.id == uuid.UUID(resp.json()["task_id"]))
            )
        ).scalar_one()
        assert task.tenant_id == TENANT_A and str(task.tenant_id) != evil

    run(check_owner())
