"""SSE endpoint tests (offline, in-memory runtime)."""

import os

# Heartbeat must be short so heartbeat tests finish quickly; must be set
# before any get_settings() call caches the singleton.
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
    async with httpx.AsyncClient(transport=transport, base_url="http://test", timeout=30) as ac:
        yield ac


async def create_task(client: httpx.AsyncClient, **overrides) -> dict:
    body = {**CREATE_BODY, **overrides}
    resp = await client.post("/api/v1/insight/tasks", json=body)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["code"] == 0
    return body["data"]["tasks"][0]


async def read_all_events(client, task_id: str, expect_terminal="COMPLETED") -> list[dict]:
    import json

    events: list[dict] = []
    async with client.stream("GET", f"/api/v1/insight/tasks/{task_id}/events") as resp:
        assert resp.headers["content-type"].startswith("text/event-stream")
        data_lines: list[str] = []
        async for line in resp.aiter_lines():
            if line.startswith("data: "):
                data_lines.append(line[len("data: ") :])
                continue
            if line == "" and data_lines:
                events.append(json.loads("".join(data_lines)))
                data_lines = []
                if events[-1]["step"] == expect_terminal:
                    break
    return events


async def test_sse_content_type_and_headers(client):
    created = await create_task(client)
    task_id = created["task_id"]
    async with client.stream("GET", f"/api/v1/insight/tasks/{task_id}/events") as resp:
        assert resp.headers["content-type"].startswith("text/event-stream")
        assert resp.headers["cache-control"] == "no-cache"
        assert resp.headers["x-accel-buffering"] == "no"


async def test_sse_full_happy_path(client):
    created = await create_task(client)
    events = await read_all_events(client, created["task_id"])
    steps = [e["step"] for e in events]
    assert "QUEUED" in steps
    for expected in (
        "FETCHING_DATA",
        "VISION_AUDIT",
        "SEMANTIC_CLUSTER",
        "DUAL_DECISION",
        "FINANCIAL_VETO",
        "EVIDENCE_TRACE",
        "COMPLETED",
    ):
        assert expected in steps
    assert steps[-1] == "COMPLETED"
    last = events[-1]
    assert set(last.keys()) == {"id", "task_id", "step", "progress", "message", "extra", "timestamp"}
    assert last["progress"] == 100


async def test_sse_failed_task(client):
    app = client._transport.app
    runtime = app.state.runtime

    from agents.workflow import build_graph
    from services.providers import DeterministicProviders

    providers = DeterministicProviders()

    async def boom(*args, **kwargs):
        raise RuntimeError("upstream exploded")

    providers.reviews.fetch = boom
    runtime.runner.graph = build_graph(providers)

    created = await create_task(client)
    events = await read_all_events(client, created["task_id"], expect_terminal="FAILED")
    steps = [e["step"] for e in events]
    assert steps[-1] == "FAILED"
    assert "upstream" in events[-1]["message"].lower()


async def test_sse_reconnect_replays_latest(client):
    created = await create_task(client)
    task_id = created["task_id"]
    events = await read_all_events(client, task_id)
    assert events[-1]["step"] == "COMPLETED"

    # Reconnect after completion: replay should end with the terminal event.
    replay = await read_all_events(client, task_id)
    assert replay[-1]["step"] == "COMPLETED"


async def test_sse_404_for_unknown_task(client):
    resp = await client.get("/api/v1/insight/tasks/tsk_nope/events")
    assert resp.status_code == 404
    body = resp.json()
    assert body["code"] == 40401


async def test_task_lifecycle_api(client):
    # detail endpoint after completion
    created = await create_task(client)
    detail_resp = await client.get(f"/api/v1/insight/tasks/{created['task_id']}")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()["data"]
    assert detail["status"] in {"RUNNING", "COMPLETED"}
    assert detail["financial_constraint"]["mold_cost_usd"] == 8000
    assert "summary" in detail

    # list endpoint
    list_resp = await client.get("/api/v1/insight/tasks?page=1&page_size=10")
    assert list_resp.status_code == 200
    data = list_resp.json()["data"]
    assert data["total"] >= 1
    assert data["items"][0]["task_id"]


async def test_create_task_validation(client):
    # invalid ASIN → 42201
    resp = await client.post("/api/v1/insight/tasks", json={"asins": ["bad-asin"]})
    assert resp.status_code == 422
    assert resp.json()["code"] == 42201

    # 11 ASINs → 40001
    resp = await client.post(
        "/api/v1/insight/tasks", json={"asins": [f"B0C1234AB{c}" for c in "ABCDEFGHIJK"]}
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == 40001

    # empty → 40001
    resp = await client.post("/api/v1/insight/tasks", json={"asins": []})
    assert resp.status_code == 400
    assert resp.json()["code"] == 40001

    # amazon_url parsing
    resp = await client.post(
        "/api/v1/insight/tasks",
        json={"amazon_url": "https://www.amazon.com/dp/B0C9999XYZ/ref=sr_1_1"},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["tasks"][0]["asin"] == "B0C9999XYZ"
