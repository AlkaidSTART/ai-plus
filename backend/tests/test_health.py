import httpx
import pytest
from httpx import ASGITransport

from main import create_app


@pytest.fixture
async def client():
    app = create_app()
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def test_app_can_be_created():
    app = create_app()
    assert app.title == "InsightX API"


async def test_health_returns_envelope(client):
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    assert body["message"] == "ok"
    data = body["data"]
    assert data["status"] == "degraded"  # no DB/Redis in the offline test env
    assert set(data.keys()) == {"status", "version", "db", "redis"}


async def test_health_fields_exist_even_without_db(client):
    resp = await client.get("/api/v1/health")
    data = resp.json()["data"]
    assert isinstance(data["db"], bool)
    assert isinstance(data["redis"], bool)


async def test_openapi_generated(client):
    resp = await client.get("/openapi.json")
    assert resp.status_code == 200
    paths = resp.json()["paths"]
    assert "/api/v1/health" in paths
    assert not any("/api/v1/api/v1" in p for p in paths)


async def test_cors_configured(client):
    resp = await client.get(
        "/api/v1/health",
        headers={"Origin": "http://localhost:5173"},
    )
    assert resp.status_code == 200


async def test_unknown_route_returns_envelope_error(client):
    resp = await client.get("/api/v1/definitely-not-a-route")
    assert resp.status_code == 404
    # Starlette 404 (no route) does not go through ApiError; envelope errors
    # are asserted on business endpoints in the API test suite.
    assert resp.json()["detail"] == "Not Found"
