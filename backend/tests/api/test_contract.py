"""P0/P1 API contract tests (docs/api.md 为契约).

前端可稳定依赖的保证：HTTP status、Envelope、字段名、类型、nullable、
枚举、分页、错误码语义、SSE payload schema 与步骤序列。
"""

import asyncio
import json
import os

os.environ.setdefault("SSE_HEARTBEAT_SECONDS", "0.2")

import httpx
import pytest
from httpx import ASGITransport

from agents.workflow import build_graph
from main import create_app
from runtime.runner import WorkflowRunner
from services.providers import DeterministicProviders, DeterministicReviewProvider

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

ENVELOPE_KEYS = {"code", "message", "data"}
TASK_DETAIL_KEYS = {
    "task_id", "asin", "product_id", "platform", "marketplace", "status",
    "current_node", "progress", "retry_count", "financial_constraint",
    "summary", "error_message", "created_at", "started_at", "finished_at",
}
TASK_SUMMARY_KEYS = {
    "review_count", "cluster_count", "proposal_count", "veto_status",
    "backtest_score", "avg_rating", "negative_review_rate",
}
TASK_STATUS_ENUM = {"PENDING", "RUNNING", "COMPLETED", "FAILED", "CANCELED"}
CLUSTER_KEYS = {
    "cluster_id", "cluster_name", "issue_type", "frequency", "frequency_ratio",
    "severity_score", "severity_level", "keywords", "sample_quotes",
    "sample_image_ids",
}
ISSUE_TYPE_ENUM = {
    "product_defect", "function_defect", "size_spec", "accessory",
    "manual", "packaging_delivery", "other",
}
SEVERITY_ENUM = {"critical", "moderate", "minor"}
PROPOSAL_KEYS = {
    "proposal_id", "task_id", "track_type", "title", "description",
    "cost_estimation_usd", "mold_opening_required", "mold_cycle_days",
    "estimated_roi", "defect_rate_reduction", "status", "veto_reason",
    "fallback_applied", "source_cluster_ids", "evidence_review_count",
    "evidence_image_count", "created_at",
}
TRACK_TYPE_ENUM = {"BODY_OPTIMIZATION", "PACKAGING_FULFILLMENT"}
PROPOSAL_STATUS_ENUM = {"PASSED", "VETOED", "PENDING"}
EVIDENCE_ITEM_KEYS = {
    "image_id", "review_id", "storage_url", "defect_category",
    "description", "confidence", "bbox", "cluster_ids",
}
DEFECT_CATEGORY_ENUM = {
    "color_difference", "broken_package", "craft_flaw", "dimension_issue", "other",
}
FINANCIAL_KEYS = {
    "task_id", "veto_status", "checked_proposals", "vetoed_proposal_ids",
    "veto_reasons", "fallback_applied", "retry_count", "financial_constraint",
}
SIMULATE_KEYS = {
    "volumetric_weight_old_kg", "volumetric_weight_new_kg", "fba_tier_old",
    "fba_tier_new", "fulfillment_saving_usd_per_unit", "monthly_profit_delta_usd",
    "payback_months", "roi", "veto_status", "veto_reasons",
    "fallback_suggestions", "payback_curve",
}
OVERVIEW_KEYS = {
    "monitored_product_count", "running_task_count", "pain_point_cluster_count",
    "fba_saving_pool_usd", "veto_triggered_count", "avg_rating",
    "negative_review_rate",
}
SSE_EVENT_KEYS = {"id", "task_id", "step", "progress", "message", "extra", "timestamp"}


@pytest.fixture
async def client():
    app = create_app()
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test", timeout=30) as ac:
        yield ac


async def create_completed_task(client, **overrides) -> str:
    body = {**CREATE_BODY, **overrides}
    task_id = (await client.post("/api/v1/insight/tasks", json=body)).json()["data"]["tasks"][0][
        "task_id"
    ]
    for _ in range(100):
        detail = (await client.get(f"/api/v1/insight/tasks/{task_id}")).json()["data"]
        if detail["status"] == "COMPLETED":
            return task_id
        assert detail["status"] != "FAILED", detail["error_message"]
        await asyncio.sleep(0.1)
    raise AssertionError("task did not complete")


# ---------------------------------------------------------------- REST 契约


async def test_health_contract(client):
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    body = resp.json()
    assert set(body.keys()) == ENVELOPE_KEYS
    assert body["code"] == 0 and body["message"] == "ok"
    data = body["data"]
    assert set(data.keys()) == {"status", "version", "db", "redis"}
    assert isinstance(data["version"], str)
    assert isinstance(data["db"], bool) and isinstance(data["redis"], bool)
    assert data["status"] in {"ok", "degraded"}


async def test_create_tasks_contract(client):
    resp = await client.post("/api/v1/insight/tasks", json=CREATE_BODY)
    assert resp.status_code == 200
    body = resp.json()
    assert set(body.keys()) == ENVELOPE_KEYS and body["code"] == 0
    tasks = body["data"]["tasks"]
    assert len(tasks) == 1
    item = tasks[0]
    assert set(item.keys()) == {
        "task_id", "asin", "product_id", "status", "cache_hit",
        "estimated_seconds", "created_at",
    }
    assert item["asin"] == "B0C1234ABC"
    assert item["status"] == "PENDING"
    assert item["cache_hit"] is False
    assert isinstance(item["estimated_seconds"], int)
    assert item["product_id"] is None  # 创建时可空


async def test_create_tasks_error_codes(client):
    # ASIN 格式不合法 → 42201
    resp = await client.post("/api/v1/insight/tasks", json={"asins": ["bad-asin"]})
    assert resp.status_code == 422 and resp.json()["code"] == 42201
    # 数量 11 → 40001
    resp = await client.post(
        "/api/v1/insight/tasks",
        json={"asins": [f"B0C1234AB{c}" for c in "ABCDEFGHIJK"]},
    )
    assert resp.status_code == 400 and resp.json()["code"] == 40001
    # 缺少 asins 与 amazon_url → 40001
    resp = await client.post("/api/v1/insight/tasks", json={"asins": []})
    assert resp.status_code == 400 and resp.json()["code"] == 40001
    # amazon_url 无法解析 → 42201
    resp = await client.post("/api/v1/insight/tasks", json={"amazon_url": "https://x.com/a"})
    assert resp.status_code == 422 and resp.json()["code"] == 42201


async def test_task_detail_contract(client):
    task_id = await create_completed_task(client)
    resp = await client.get(f"/api/v1/insight/tasks/{task_id}")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert set(data.keys()) == TASK_DETAIL_KEYS
    assert data["status"] in TASK_STATUS_ENUM
    assert data["platform"] == "amazon" and data["marketplace"] == "US"
    assert isinstance(data["progress"], int) and 0 <= data["progress"] <= 100
    assert isinstance(data["retry_count"], int)
    # COMPLETED 时 nullable 字段收敛
    assert data["error_message"] is None
    assert data["started_at"] is not None and data["finished_at"] is not None
    summary = data["summary"]
    assert set(summary.keys()) == TASK_SUMMARY_KEYS
    assert summary["veto_status"] in {"PENDING", "PASSED", "VETOED"}
    for key in ("review_count", "cluster_count", "proposal_count"):
        assert isinstance(summary[key], int)


async def test_task_list_contract_and_pagination(client):
    task_id = await create_completed_task(client)
    resp = await client.get("/api/v1/insight/tasks?page=1&page_size=10")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert set(data.keys()) == {"items", "total", "page", "page_size"}
    assert data["page"] == 1 and data["page_size"] == 10
    assert data["total"] >= 1
    assert set(data["items"][0].keys()) == TASK_DETAIL_KEYS

    # 过滤参数生效
    resp = await client.get("/api/v1/insight/tasks?status=COMPLETED&asin=B0C1234ABC")
    assert resp.status_code == 200
    assert all(i["status"] == "COMPLETED" for i in resp.json()["data"]["items"])

    # 分页参数校验 → 42201
    resp = await client.get("/api/v1/insight/tasks?page=0")
    assert resp.status_code == 422 and resp.json()["code"] == 42201
    resp = await client.get("/api/v1/insight/tasks?page_size=101")
    assert resp.status_code == 422 and resp.json()["code"] == 42201


async def test_clusters_contract(client):
    task_id = await create_completed_task(client)
    resp = await client.get(f"/api/v1/insight/tasks/{task_id}/clusters")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert set(data.keys()) == {"items", "total", "page", "page_size"}
    for c in data["items"]:
        assert set(c.keys()) == CLUSTER_KEYS
        assert c["issue_type"] in ISSUE_TYPE_ENUM
        assert c["severity_level"] in SEVERITY_ENUM
        assert isinstance(c["frequency"], int)
        assert isinstance(c["frequency_ratio"], float)
        assert isinstance(c["keywords"], list)
        for quote in c["sample_quotes"]:
            assert {"review_id", "language", "content", "translated_content", "rating"} <= set(
                quote.keys()
            )


async def test_proposals_contract(client):
    task_id = await create_completed_task(client)
    resp = await client.get(f"/api/v1/insight/tasks/{task_id}/proposals")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert set(data.keys()) == {"items", "total"}
    for p in data["items"]:
        assert set(p.keys()) >= PROPOSAL_KEYS
        assert p["track_type"] in TRACK_TYPE_ENUM
        assert p["status"] in PROPOSAL_STATUS_ENUM
        assert isinstance(p["mold_opening_required"], bool)
        assert isinstance(p["fallback_applied"], bool)
        assert isinstance(p["source_cluster_ids"], list)
        assert isinstance(p["created_at"], str)
        if p["track_type"] == "PACKAGING_FULFILLMENT":
            for key in (
                "package_size_old_cm", "package_size_new_cm",
                "volumetric_weight_old_kg", "volumetric_weight_new_kg",
                "fba_tier_old", "fba_tier_new", "fulfillment_saving_usd_per_unit",
            ):
                assert key in p, f"包装轨缺少 {key}"
    # track_type 过滤
    resp = await client.get(
        f"/api/v1/insight/tasks/{task_id}/proposals?track_type=PACKAGING_FULFILLMENT"
    )
    assert all(
        p["track_type"] == "PACKAGING_FULFILLMENT" for p in resp.json()["data"]["items"]
    )


async def test_visual_evidences_contract(client):
    task_id = await create_completed_task(client)
    resp = await client.get(f"/api/v1/insight/tasks/{task_id}/visual-evidences")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert set(data.keys()) == {"items", "total", "page", "page_size"}
    for e in data["items"]:
        assert set(e.keys()) == EVIDENCE_ITEM_KEYS
        assert e["defect_category"] in DEFECT_CATEGORY_ENUM
        assert isinstance(e["confidence"], float)
        assert isinstance(e["bbox"], list)


async def test_financial_contract(client):
    task_id = await create_completed_task(client)
    resp = await client.get(f"/api/v1/insight/tasks/{task_id}/financial")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert set(data.keys()) == FINANCIAL_KEYS
    assert data["veto_status"] in {"PASSED", "VETOED", "PENDING"}
    assert isinstance(data["vetoed_proposal_ids"], list)
    assert isinstance(data["fallback_applied"], bool)


async def test_financial_simulate_contract(client):
    resp = await client.post(
        "/api/v1/financial/simulate",
        json={
            "mold_cost_usd": 8000,
            "moq": 1000,
            "current_gross_margin": 0.32,
            "expected_price_usd": 29.99,
            "unit_cost_increase_usd": 1.8,
            "package_size_old_cm": [30, 20, 12],
            "package_size_new_cm": [26, 18, 9],
            "expected_return_rate_reduction": 0.35,
        },
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert set(data.keys()) == SIMULATE_KEYS
    assert data["veto_status"] in {"PASSED", "VETOED"}
    assert isinstance(data["payback_curve"], list) and len(data["payback_curve"]) == 3
    for point in data["payback_curve"]:
        assert {"return_rate_reduction", "payback_months"} <= set(point.keys())
    # 参数校验 → 42201
    resp = await client.post("/api/v1/financial/simulate", json={"current_gross_margin": 5})
    assert resp.status_code == 422 and resp.json()["code"] == 42201


async def test_products_contract(client):
    resp = await client.get("/api/v1/products?page=1&page_size=5")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert set(data.keys()) == {"items", "total", "page", "page_size"}
    for p in data["items"]:
        assert {
            "product_id", "asin", "platform", "marketplace", "title", "category",
            "current_price", "currency", "main_image_url", "review_count",
            "avg_rating", "bsr", "updated_at",
        } <= set(p.keys())
        assert p["currency"] == "USD"


async def test_products_reviews_contract(client):
    # 先取一个真实商品（Docker/本地 DB 有数据时），否则跳过内容断言
    listing = (await client.get("/api/v1/products")).json()["data"]
    if not listing["items"]:
        pytest.skip("无商品数据（离线无 DB 环境）")
    product_id = listing["items"][0]["product_id"]
    resp = await client.get(f"/api/v1/products/{product_id}/reviews?page=1&page_size=5")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert set(data.keys()) == {"items", "total", "page", "page_size"}
    for r in data["items"]:
        assert {
            "review_id", "rating", "review_date", "language", "title", "content",
            "translated_content", "verified_purchase", "helpful_votes",
            "image_urls", "cluster_ids",
        } <= set(r.keys())
        assert 0 <= r["rating"] <= 5
        assert isinstance(r["verified_purchase"], bool)


async def test_dashboard_contract(client):
    await create_completed_task(client)
    resp = await client.get("/api/v1/dashboard/overview")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert set(data.keys()) == OVERVIEW_KEYS
    for key in (
        "monitored_product_count", "running_task_count",
        "pain_point_cluster_count", "fba_saving_pool_usd", "veto_triggered_count",
    ):
        assert isinstance(data[key], (int, float))

    resp = await client.get("/api/v1/dashboard/recommendations")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert set(data.keys()) == {"items", "total", "page", "page_size"}
    for item in data["items"]:
        assert {
            "task_id", "product_id", "asin", "title", "main_image_url",
            "estimated_roi", "return_rate_reduction", "veto_status", "finished_at",
        } <= set(item.keys())
        assert item["veto_status"] in {"PENDING", "PASSED", "VETOED"}


async def test_report_contract(client):
    task_id = await create_completed_task(client)
    resp = await client.get(f"/api/v1/insight/tasks/{task_id}/report")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert set(data.keys()) == {
        "task", "clusters", "proposals", "financial", "visual_evidences"
    }
    assert set(data["task"].keys()) == TASK_DETAIL_KEYS
    assert {"items"} <= set(data["clusters"].keys())
    assert {"items"} <= set(data["proposals"].keys())
    assert {"items"} <= set(data["visual_evidences"].keys())


async def test_error_codes_contract(client):
    # 40401 系列
    for path in (
        "/api/v1/insight/tasks/tsk_none",
        "/api/v1/insight/tasks/tsk_none/report",
        "/api/v1/insight/tasks/tsk_none/clusters",
        "/api/v1/insight/tasks/tsk_none/proposals",
        "/api/v1/insight/tasks/tsk_none/visual-evidences",
        "/api/v1/insight/tasks/tsk_none/financial",
        "/api/v1/proposals/prp_none",
        "/api/v1/proposals/prp_none/evidence",
    ):
        resp = await client.get(path)
        assert resp.status_code == 404, path
        body = resp.json()
        assert body["code"] == 40401, path
        assert set(body.keys()) == ENVELOPE_KEYS

    # 40901：对 COMPLETED 任务 cancel / retry
    task_id = await create_completed_task(client)
    resp = await client.post(f"/api/v1/insight/tasks/{task_id}/cancel")
    assert resp.status_code == 409 and resp.json()["code"] == 40901
    resp = await client.post(f"/api/v1/insight/tasks/{task_id}/retry")
    assert resp.status_code == 409 and resp.json()["code"] == 40901

    # 40901：任务未完成时请求 report
    resp = await client.post("/api/v1/insight/tasks", json=CREATE_BODY)
    fresh_id = resp.json()["data"]["tasks"][0]["task_id"]
    detail = (await client.get(f"/api/v1/insight/tasks/{fresh_id}")).json()["data"]
    if detail["status"] != "COMPLETED":
        resp = await client.get(f"/api/v1/insight/tasks/{fresh_id}/report")
        assert resp.status_code == 409 and resp.json()["code"] == 40901

    # 50201：无正式数据源的 price-history
    resp = await client.get("/api/v1/products/00000000-0000-0000-0000-000000000000/price-history")
    assert resp.status_code == 502 and resp.json()["code"] == 50201


# ---------------------------------------------------------------- SSE 契约

SSE_NODE_STEPS = [
    "QUEUED",
    "FETCHING_DATA",
    "VISION_AUDIT",
    "SEMANTIC_CLUSTER",
    "DUAL_DECISION",
    "FINANCIAL_VETO",
    "EVIDENCE_TRACE",
    "COMPLETED",
]


async def read_sse(client, task_id: str, terminal: str = "COMPLETED") -> list[dict]:
    events = []
    buf: list[str] = []
    async with client.stream("GET", f"/api/v1/insight/tasks/{task_id}/events") as stream:
        assert stream.headers["content-type"].startswith("text/event-stream")
        assert stream.headers["cache-control"] == "no-cache"
        assert stream.headers["x-accel-buffering"] == "no"
        async for line in stream.aiter_lines():
            if line.startswith("data: "):
                buf.append(line[6:])
            elif line == "" and buf:
                events.append(json.loads("".join(buf)))
                buf = []
                if events[-1]["step"] == terminal:
                    break
    return events


async def test_sse_event_schema_and_step_sequence(client):
    task_id = await create_completed_task(client)
    events = await read_sse(client, task_id)
    steps = [e["step"] for e in events]

    # 步骤序列：QUEUED 开头、COMPLETED 结尾、节点步骤按序出现
    assert steps[0] == "QUEUED" and steps[-1] == "COMPLETED"
    ordered = [s for s in steps if s in SSE_NODE_STEPS]
    assert ordered == SSE_NODE_STEPS
    # BACKTEST_EVAL 仅实际执行时出现；P2 未实现且默认关闭 → 不出现
    assert "BACKTEST_EVAL" not in steps

    for e in events:
        assert set(e.keys()) == SSE_EVENT_KEYS
        assert isinstance(e["task_id"], str) and e["task_id"] == task_id
        assert isinstance(e["progress"], int)
        assert isinstance(e["message"], str)
        assert isinstance(e["extra"], dict)
        assert isinstance(e["timestamp"], str)
        assert e["step"] in set(SSE_NODE_STEPS) | {"BACKTEST_EVAL", "FAILED", "CANCELED"}
    # COMPLETED 进度为 100
    assert events[-1]["progress"] == 100


async def test_sse_failed_event(client):
    app = client._transport.app
    runtime = app.state.runtime
    providers = DeterministicProviders()

    async def boom(*args, **kwargs):
        raise RuntimeError("upstream exploded")

    providers.reviews.fetch = boom
    runtime.runner = WorkflowRunner(build_graph(providers), runtime.task_store, runtime.event_store)

    task_id = (await client.post("/api/v1/insight/tasks", json=CREATE_BODY)).json()["data"][
        "tasks"
    ][0]["task_id"]
    events = await read_sse(client, task_id, terminal="FAILED")
    assert events[-1]["step"] == "FAILED"
    assert "upstream" in events[-1]["message"]


async def test_sse_backtest_enabled_fails_with_p2_message(client):
    resp = await client.post(
        "/api/v1/insight/tasks",
        json={**CREATE_BODY, "options": {"enable_backtest": True, "enable_vision_audit": True}},
    )
    task_id = resp.json()["data"]["tasks"][0]["task_id"]
    events = await read_sse(client, task_id, terminal="FAILED")
    assert events[-1]["step"] == "FAILED"
    assert "P2 历史回测" in events[-1]["message"]


async def test_sse_canceled(client):
    app = client._transport.app
    runtime = app.state.runtime
    providers = DeterministicProviders()
    original_fetch = providers.reviews.fetch

    async def slow_fetch(*args, **kwargs):
        await asyncio.sleep(0.3)
        return await original_fetch(*args, **kwargs)

    providers.reviews.fetch = slow_fetch
    runtime.runner = WorkflowRunner(build_graph(providers), runtime.task_store, runtime.event_store)

    task_id = (await client.post("/api/v1/insight/tasks", json=CREATE_BODY)).json()["data"][
        "tasks"
    ][0]["task_id"]

    # 后台读完整个流（直到 CANCELED），主协程在看到 RUNNING 后取消
    reader_events: list[dict] = []

    async def reader():
        buf: list[str] = []
        async with client.stream("GET", f"/api/v1/insight/tasks/{task_id}/events") as stream:
            async for line in stream.aiter_lines():
                if line.startswith("data: "):
                    buf.append(line[6:])
                elif line == "" and buf:
                    ev = json.loads("".join(buf))
                    buf = []
                    reader_events.append(ev)
                    if ev["step"] == "CANCELED":
                        return

    task = asyncio.create_task(asyncio.wait_for(reader(), timeout=10))
    for _ in range(50):
        detail = (await client.get(f"/api/v1/insight/tasks/{task_id}")).json()["data"]
        if detail["status"] in ("RUNNING", "COMPLETED"):
            break
        await asyncio.sleep(0.02)
    resp = await client.post(f"/api/v1/insight/tasks/{task_id}/cancel")
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "CANCELED"

    await task
    steps = [e["step"] for e in reader_events]
    assert "CANCELED" in steps
    # 取消后任务不再继续推进到 COMPLETED
    detail = (await client.get(f"/api/v1/insight/tasks/{task_id}")).json()["data"]
    assert detail["status"] == "CANCELED"


async def test_sse_replay_and_reconnect(client):
    task_id = await create_completed_task(client)
    # 第一次读完（COMPLETED 关流）
    first = await read_sse(client, task_id)
    assert first[-1]["step"] == "COMPLETED"
    # 重连：重放最近事件，仍以终态收尾并关闭
    second = await read_sse(client, task_id)
    assert second[-1]["step"] == "COMPLETED"
    ids_first = {e["id"] for e in first}
    assert all(e["id"] in ids_first for e in second)


async def test_sse_heartbeat_on_idle(client):
    runtime = client._transport.app.state.runtime
    from runtime.task_store import TaskRecord

    await runtime.task_store.create(TaskRecord(task_id="tsk_contract_idle", asin="B0C1234ABC"))
    got_ping = False
    async with client.stream("GET", "/api/v1/insight/tasks/tsk_contract_idle/events") as stream:
        async def _read():
            nonlocal got_ping
            async for line in stream.aiter_lines():
                if line.startswith(": ping"):
                    got_ping = True
                    return
        await asyncio.wait_for(_read(), timeout=3)
    assert got_ping
