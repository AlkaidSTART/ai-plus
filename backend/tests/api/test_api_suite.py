"""Step 4 API tests: full P0/P1 endpoint suite (offline)."""

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
    async with httpx.AsyncClient(transport=transport, base_url="http://test", timeout=30) as ac:
        yield ac


async def create_completed_task(client) -> str:
    resp = await client.post("/api/v1/insight/tasks", json=CREATE_BODY)
    assert resp.status_code == 200
    task_id = resp.json()["data"]["tasks"][0]["task_id"]
    # wait for completion
    for _ in range(100):
        detail = (await client.get(f"/api/v1/insight/tasks/{task_id}")).json()["data"]
        if detail["status"] == "COMPLETED":
            return task_id
        if detail["status"] == "FAILED":
            raise AssertionError(detail["error_message"])
        await asyncio.sleep(0.1)
    raise AssertionError("task did not complete in time")


import asyncio


async def test_full_p0_chain(client):
    """POST task → SSE → COMPLETED → report → clusters → proposals → evidence → financial."""
    task_id = await create_completed_task(client)

    report = (await client.get(f"/api/v1/insight/tasks/{task_id}/report")).json()
    assert report["code"] == 0
    assert report["data"]["task"]["status"] == "COMPLETED"
    assert report["data"]["clusters"]["items"]
    assert report["data"]["proposals"]["items"]
    assert report["data"]["financial"]["veto_status"] == "PASSED"

    clusters = (await client.get(f"/api/v1/insight/tasks/{task_id}/clusters")).json()["data"]
    assert clusters["total"] == 5
    cluster = clusters["items"][0]
    assert cluster["severity_level"] in {"critical", "moderate", "minor"}
    assert set(cluster.keys()) >= {
        "cluster_id", "cluster_name", "issue_type", "frequency", "frequency_ratio",
        "severity_score", "severity_level", "keywords", "sample_quotes", "sample_image_ids",
    }

    proposals = (await client.get(f"/api/v1/insight/tasks/{task_id}/proposals")).json()["data"]
    assert proposals["items"]
    proposal = proposals["items"][0]
    assert proposal["track_type"] in {"BODY_OPTIMIZATION", "PACKAGING_FULFILLMENT"}

    detail = (await client.get(f"/api/v1/proposals/{proposal['proposal_id']}")).json()
    assert detail["code"] == 0
    assert detail["data"]["proposal_id"] == proposal["proposal_id"]

    evidence = (await client.get(f"/api/v1/proposals/{proposal['proposal_id']}/evidence")).json()
    assert evidence["code"] == 0
    assert evidence["data"]["proposal_id"] == proposal["proposal_id"]
    assert evidence["data"]["total"] > 0
    review = evidence["data"]["reviews"][0]
    assert review["review_id"] and review["content"]

    financial = (await client.get(f"/api/v1/insight/tasks/{task_id}/financial")).json()
    assert financial["code"] == 0
    assert financial["data"]["checked_proposals"] == len(proposals["items"])


async def test_visual_evidences_endpoint(client):
    task_id = await create_completed_task(client)
    resp = await client.get(
        f"/api/v1/insight/tasks/{task_id}/visual-evidences?min_confidence=0.5"
    )
    data = resp.json()["data"]
    assert data["total"] > 0
    item = data["items"][0]
    assert set(item.keys()) >= {
        "image_id", "review_id", "storage_url", "defect_category",
        "description", "confidence", "bbox",
    }
    # 过滤器
    resp = await client.get(
        f"/api/v1/insight/tasks/{task_id}/visual-evidences?defect_category=other"
    )
    data2 = resp.json()["data"]
    assert data2["total"] <= data["total"]


async def test_report_conflict_when_not_completed(client):
    resp = await client.post("/api/v1/insight/tasks", json=CREATE_BODY)
    task_id = resp.json()["data"]["tasks"][0]["task_id"]
    # 立刻请求 report：任务大概率未完成（或恰好完成，两种都合法）
    detail = (await client.get(f"/api/v1/insight/tasks/{task_id}")).json()["data"]
    report_resp = await client.get(f"/api/v1/insight/tasks/{task_id}/report")
    if detail["status"] != "COMPLETED":
        assert report_resp.status_code == 409
        assert report_resp.json()["code"] == 40901


async def test_cancel_conflict_on_completed(client):
    task_id = await create_completed_task(client)
    resp = await client.post(f"/api/v1/insight/tasks/{task_id}/cancel")
    assert resp.status_code == 409
    assert resp.json()["code"] == 40901


async def test_retry_conflict_on_completed(client):
    task_id = await create_completed_task(client)
    resp = await client.post(f"/api/v1/insight/tasks/{task_id}/retry")
    assert resp.status_code == 409
    assert resp.json()["code"] == 40901


async def test_404s(client):
    for path in (
        "/api/v1/insight/tasks/tsk_none",
        "/api/v1/insight/tasks/tsk_none/report",
        "/api/v1/insight/tasks/tsk_none/clusters",
        "/api/v1/insight/tasks/tsk_none/financial",
        "/api/v1/insight/tasks/tsk_none/visual-evidences",
        "/api/v1/proposals/prp_none",
        "/api/v1/proposals/prp_none/evidence",
    ):
        resp = await client.get(path)
        assert resp.status_code == 404, path
        assert resp.json()["code"] == 40401, path


async def test_dashboard_overview_and_recommendations(client):
    await create_completed_task(client)
    overview = (await client.get("/api/v1/dashboard/overview")).json()["data"]
    assert overview["monitored_product_count"] >= 1
    assert overview["pain_point_cluster_count"] >= 5
    assert "fba_saving_pool_usd" in overview
    assert "avg_rating" in overview

    recs = (await client.get("/api/v1/dashboard/recommendations")).json()["data"]
    assert recs["total"] >= 1
    item = recs["items"][0]
    assert set(item.keys()) >= {
        "task_id", "asin", "estimated_roi", "return_rate_reduction", "veto_status",
    }


async def test_financial_simulate(client):
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
    assert {"roi", "payback_months", "veto_status", "payback_curve"} <= set(data.keys())
    # 无副作用：不创建任务
    tasks = (await client.get("/api/v1/insight/tasks")).json()["data"]
    assert tasks["total"] == 0


async def test_financial_simulate_validation(client):
    resp = await client.post("/api/v1/financial/simulate", json={"current_gross_margin": 5})
    assert resp.status_code == 422
    assert resp.json()["code"] == 42201


async def test_products_endpoints_offline(client):
    # 无数据库时如实返回空列表 / 404，而不是伪造数据；
    # 有数据库时返回真实行——两种环境都必须合法
    resp = await client.get("/api/v1/products")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    assert isinstance(body["data"]["items"], list)
    assert body["data"]["total"] >= len(body["data"]["items"])

    resp = await client.get("/api/v1/products/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404
    assert resp.json()["code"] == 40401

    resp = await client.get("/api/v1/products/00000000-0000-0000-0000-000000000000/price-history")
    assert resp.status_code == 502
    assert resp.json()["code"] == 50201

    resp = await client.get("/api/v1/products/00000000-0000-0000-0000-000000000000/reviews")
    assert resp.status_code == 404


async def test_pagination_params_validated(client):
    resp = await client.get("/api/v1/insight/tasks?page=0")
    assert resp.status_code == 422
    resp = await client.get("/api/v1/insight/tasks?page_size=101")
    assert resp.status_code == 422
    resp = await client.get("/api/v1/insight/tasks?page=1&page_size=5")
    assert resp.status_code == 200
    assert resp.json()["data"]["page_size"] == 5


async def test_openapi_has_all_p0_paths(client):
    resp = await client.get("/openapi.json")
    paths = resp.json()["paths"]
    expected = [
        "/api/v1/health",
        "/api/v1/insight/tasks",
        "/api/v1/insight/tasks/{task_id}",
        "/api/v1/insight/tasks/{task_id}/events",
        "/api/v1/insight/tasks/{task_id}/cancel",
        "/api/v1/insight/tasks/{task_id}/retry",
        "/api/v1/insight/tasks/{task_id}/report",
        "/api/v1/insight/tasks/{task_id}/clusters",
        "/api/v1/insight/tasks/{task_id}/visual-evidences",
        "/api/v1/dashboard/overview",
        "/api/v1/dashboard/recommendations",
        "/api/v1/products",
        "/api/v1/products/{product_id}",
        "/api/v1/products/{product_id}/price-history",
        "/api/v1/products/{product_id}/reviews",
        "/api/v1/proposals/{proposal_id}",
        "/api/v1/proposals/{proposal_id}/evidence",
        "/api/v1/financial/simulate",
        "/api/v1/insight/tasks/{task_id}/financial",
    ]
    for path in expected:
        assert path in paths, f"missing {path}"
    assert not any("/api/v1/api/v1" in p for p in paths)
