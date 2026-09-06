"""SSE robustness tests: heartbeat, client disconnect, no-hang guarantees."""

import asyncio
import os

os.environ.setdefault("SSE_HEARTBEAT_SECONDS", "0.2")

import httpx
import pytest
from httpx import ASGITransport

from main import create_app

CREATE_BODY = {
    "asins": ["B0C1234ABC"],
    "financial_constraint": {
        "mold_cost_usd": 8000,
        "moq": 1000,
        "current_gross_margin": 0.32,
        "expected_price_usd": 29.99,
        "unit_cost_increase_usd": 1.8,
    },
}


@pytest.fixture
async def client():
    app = create_app()
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test", timeout=10) as ac:
        yield ac


async def test_sse_heartbeat_when_idle(client):
    """Connected but no new events → server must emit `: ping` comments."""
    # 直接写入任务存储且不调度 runner：SSE 流将保持空闲
    runtime = client._transport.app.state.runtime
    from runtime.task_store import TaskRecord

    task = TaskRecord(task_id="tsk_idle", asin="B0C1234ABC")
    await runtime.task_store.create(task)

    got_ping = False
    async with client.stream("GET", "/api/v1/insight/tasks/tsk_idle/events") as stream:
        deadline = asyncio.get_event_loop().time() + 3

        async def _read():
            nonlocal got_ping
            async for line in stream.aiter_lines():
                if line.startswith(": ping"):
                    got_ping = True
                    return

        await asyncio.wait_for(_read(), timeout=3)
    assert got_ping, "空闲 SSE 连接应在心跳周期内收到 : ping"


async def test_sse_client_disconnect_does_not_break_server(client):
    resp = await client.post("/api/v1/insight/tasks", json=CREATE_BODY)
    task_id = resp.json()["data"]["tasks"][0]["task_id"]

    # 连接后提前退出（客户端断连）
    async with client.stream("GET", f"/api/v1/insight/tasks/{task_id}/events") as stream:
        async for _line in stream.aiter_lines():
            break  # 读完第一行即断开

    # 服务端仍然健康、任务仍然能完成
    for _ in range(100):
        detail = (await client.get(f"/api/v1/insight/tasks/{task_id}")).json()["data"]
        if detail["status"] == "COMPLETED":
            break
        await asyncio.sleep(0.1)
    assert detail["status"] == "COMPLETED"

    health = (await client.get("/api/v1/health")).status_code
    assert health == 200


async def test_sse_tests_have_timeout_guards(client):
    """Regression guard: any SSE stream read must be bounded."""
    resp = await client.post("/api/v1/insight/tasks", json=CREATE_BODY)
    task_id = resp.json()["data"]["tasks"][0]["task_id"]

    async def _read_all():
        async with client.stream("GET", f"/api/v1/insight/tasks/{task_id}/events") as stream:
            async for _line in stream.aiter_lines():
                pass

    try:
        await asyncio.wait_for(_read_all(), timeout=10)
    except asyncio.TimeoutError:
        pytest.fail("SSE stream hung beyond 10s")
    except Exception:  # noqa: BLE001 - early close etc.
        pass
