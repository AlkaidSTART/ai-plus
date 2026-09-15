"""Tests for competitor radar endpoints: BSR trends and cross-platform matrix."""

from __future__ import annotations

from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import BigInteger, create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from insightx.database import Base, get_session
from insightx.main import create_app
from insightx.models import Task, TaskItem


@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(type_: Any, compiler: Any, **kw: Any) -> str:
    del type_, compiler, kw
    return "JSON"


@compiles(BigInteger, "sqlite")
def compile_bigint_sqlite(type_: Any, compiler: Any, **kw: Any) -> str:
    del type_, compiler, kw
    return "INTEGER"


@pytest.fixture
def session_factory():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as session:
        session.add(
            Task(
                task_id="tsk_radar_1",
                tenant_id="dev-tenant",
                platform="amazon",
                marketplace="US",
                window_preset="6m",
                status="COMPLETED",
            )
        )
        session.add(
            TaskItem(
                item_id="itm_radar_1",
                task_id="tsk_radar_1",
                tenant_id="dev-tenant",
                asin="B08N5WRWNW",
                status="COMPLETED",
            )
        )
        session.commit()
    return factory


@pytest.fixture
async def client(session_factory):
    app = create_app()

    def override_session():
        with session_factory() as s:
            yield s

    app.dependency_overrides[get_session] = override_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def test_bsr_trends_default(client: AsyncClient):
    res = await client.get("/api/v1/radar/bsr-trends")
    assert res.status_code == 200
    body = res.json()
    assert body["code"] == 0
    assert body["message"] == "ok"
    data = body["data"]
    assert "items" in data
    assert len(data["items"]) >= 3
    first = data["items"][0]
    assert "asin" in first
    assert "current_bsr" in first
    assert "current_price" in first
    assert "history" in first
    assert len(first["history"]) > 0


async def test_bsr_trends_with_filters(client: AsyncClient):
    res = await client.get(
        "/api/v1/radar/bsr-trends", params={"asin": "B08N5WRWNW", "days": 7}
    )
    assert res.status_code == 200
    body = res.json()
    data = body["data"]
    assert len(data["items"]) == 1
    item = data["items"][0]
    assert item["asin"] == "B08N5WRWNW"
    assert len(item["history"]) >= 7


async def test_cross_platform_default(client: AsyncClient):
    res = await client.get("/api/v1/radar/cross-platform")
    assert res.status_code == 200
    body = res.json()
    assert body["code"] == 0
    data = body["data"]
    assert "metrics" in data
    assert "items" in data
    metrics = data["metrics"]
    assert metrics["total_skus"] >= 6
    assert metrics["avg_match_score"] > 0.0
    first_item = data["items"][0]
    assert first_item["platform"] in ("TIKTOK", "TEMU")
    assert first_item["estimated_fees"] > 0
    assert "estimated_spread" in first_item


async def test_cross_platform_filters(client: AsyncClient):
    res = await client.get(
        "/api/v1/radar/cross-platform",
        params={"platform": "TIKTOK", "status": "MATCHED"},
    )
    assert res.status_code == 200
    body = res.json()
    data = body["data"]
    for item in data["items"]:
        assert item["platform"] == "TIKTOK"
        assert item["match_status"] == "MATCHED"
