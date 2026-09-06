"""Failure semantics tests (Step 5 §十四)."""

import pytest

from core.llm import FakeLLMClient, LLMError, extract_json
from services.financial import FinancialEngine


def test_llm_invalid_json_raises_llmerror():
    with pytest.raises(LLMError):
        extract_json("this is not json at all")


def test_llm_extract_json_fenced():
    assert extract_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert extract_json('prefix {"a": 1} suffix') == {"a": 1}


def test_fake_llm_structured():
    from pydantic import BaseModel

    class Out(BaseModel):
        x: int

    client = FakeLLMClient(canned={"x": 5})
    import asyncio

    result = asyncio.run(client.complete_structured("p", Out))
    assert result.x == 5


def test_financial_engine_payback_curve_monotonic():
    engine = FinancialEngine()
    result = engine.simulate(
        {
            "mold_cost_usd": 8000,
            "moq": 1000,
            "current_gross_margin": 0.32,
            "expected_price_usd": 29.99,
            "unit_cost_increase_usd": 1.8,
            "expected_return_rate_reduction": 0.35,
        }
    )
    curve = [p["payback_months"] for p in result["payback_curve"]]
    assert curve == sorted(curve, reverse=True), "退货率降低越多，回本周期应越短"


def test_upstream_error_maps_to_50201():
    from api.errors import ApiError, ErrorCode

    err = ApiError(ErrorCode.UPSTREAM, "upstream failed")
    assert err.code == 50201
    assert err.http_status == 502


def test_no_stack_trace_in_error_envelope():
    """Unhandled exception handler must not leak internals (string check)."""
    import asyncio

    import httpx
    from httpx import ASGITransport

    from main import create_app

    app = create_app()

    @app.get("/api/v1/__boom")
    async def boom():
        raise RuntimeError("secret internal detail ABCXYZ")

    async def run():
        transport = ASGITransport(app=app, raise_app_exceptions=False)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/__boom")
            return resp.status_code, resp.json()

    status, body = asyncio.run(run())
    assert status == 500
    assert body["code"] == 50001
    assert "ABCXYZ" not in body["message"]
