"""事件与 SSE 测试：格式化纯函数离线可跑；流行为需隔离库。"""

import uuid

from sqlalchemy import func, select

from app.services import events as event_svc
from tests.support import requires_pg, run
from tests.test_tasks import PROJECT_A, TENANT_A, make_client, seed_tenant_project


def test_format_sse():
    text = event_svc.format_sse("node.updated", '{"a": 1}', "13")
    assert text == 'id: 13\nevent: node.updated\ndata: {"a": 1}\n\n'


def test_format_comment():
    assert event_svc.format_comment() == ": heartbeat\n\n"


def test_parse_after():
    assert event_svc.parse_after("0") == 0
    assert event_svc.parse_after("12") == 12
    for bad in ("-1", "abc", "", "1.5"):
        try:
            event_svc.parse_after(bad)
        except ValueError:
            continue
        raise AssertionError(f"应拒绝游标：{bad!r}")


def test_business_event_mapping():
    name, eid, data = event_svc.business_event_to_sse(
        "task-1", 7, "node.updated",
        {"node": "clustering", "status": "COMPLETED"},
    )
    assert (name, eid) == ("node.updated", "7")
    assert '"seq": 7' in data and '"schema_version": 1' in data


def test_stream_end_payload():
    assert "stream" not in event_svc.stream_end_payload("9", "COMPLETED")
    assert '"last_event_id": "9"' in event_svc.stream_end_payload("9", "COMPLETED")


@requires_pg
def test_append_seq_ordered(pg_session):
    from app.services import tasks as task_svc
    from tests.test_tasks import create_kwargs

    async def main():
        await seed_tenant_project(pg_session, TENANT_A, PROJECT_A)
        created = await task_svc.create_task(pg_session, **create_kwargs())
        task_id = uuid.UUID(created["task_id"])
        seqs = [
            await event_svc.append_event(
                pg_session, tenant_id=TENANT_A, task_id=task_id,
                event_type="warning", payload={"code": "W", "message": "m"},
            )
            for _ in range(3)
        ]
        assert seqs == [2, 3, 4]
        events = await event_svc.read_events(pg_session, task_id, 1)
        assert [e.seq for e in events] == [2, 3, 4]
        assert [e.seq for e in await event_svc.read_events(pg_session, task_id, 3)] == [4]

    run(main())


@requires_pg
def test_sse_replay_and_end(pg_session):
    from app.worker import graph as worker_graph

    async def seed():
        await seed_tenant_project(pg_session, TENANT_A, PROJECT_A)

    run(seed())
    client = make_client(pg_session, TENANT_A)
    task_id = client.post(
        "/api/v1/insight/task",
        headers={"Idempotency-Key": "sse-k1"},
        json={"project_id": str(PROJECT_A), "asins": ["B011111111"]},
    ).json()["task_id"]

    async def settle():
        await worker_graph.finalize_task(
            pg_session, tenant_id=TENANT_A, task_id=uuid.UUID(task_id)
        )

    run(settle())
    stream = client.get(f"/api/v1/insight/task/{task_id}/events?after=0")
    assert stream.status_code == 200
    assert stream.headers["content-type"].startswith("text/event-stream")
    body = stream.text
    assert "retry: 3000" in body
    assert "event: task.updated" in body
    assert "event: task.canceled" in body
    assert "event: stream.end" in body

    bad_cursor = client.get(f"/api/v1/insight/task/{task_id}/events?after=abc")
    assert bad_cursor.status_code == 422
    assert bad_cursor.json()["error"]["code"] == "INVALID_EVENT_CURSOR"
    ahead = client.get(f"/api/v1/insight/task/{task_id}/events?after=99999")
    assert ahead.status_code == 422
    unknown = client.get(f"/api/v1/insight/task/{uuid.uuid4()}/events?after=0")
    assert unknown.status_code == 404


@requires_pg
def test_sse_tenant_isolation(pg_session):
    from tests.test_tasks import TENANT_B

    other = make_client(pg_session, TENANT_B)
    resp = other.get(f"/api/v1/insight/task/{uuid.uuid4()}/events?after=0")
    assert resp.status_code == 404
