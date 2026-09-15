"""Tests for financial risk evaluation and circuit breaker."""

import pytest
from httpx import ASGITransport, AsyncClient

from insightx.main import create_app
from insightx.schemas import FinancialEvaluateRequest, FinancialState
from insightx.services.financial import evaluate_financial_risk, get_financial_rules


@pytest.fixture
async def client():
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


def test_financial_rules_metadata():
    rules = get_financial_rules()
    assert rules.rule_version == "financial_rules_v1.0"
    assert len(rules.rules) == 4
    codes = {r.code for r in rules.rules}
    assert codes == {
        "NEGATIVE_MARGIN",
        "MOLD_COST_RATIO_EXCEEDED",
        "PAYBACK_PERIOD_EXCEEDED",
        "BUDGET_EXCEEDED",
    }


def test_financial_evaluate_missing_inputs_returns_not_evaluated():
    # Empty request
    req = FinancialEvaluateRequest()
    res = evaluate_financial_risk(req)
    assert res.financial_state == FinancialState.NOT_EVALUATED
    assert not res.circuit_breaker_triggered
    assert res.metrics is None
    assert len(res.reasons) > 0
    assert "NOT_EVALUATED" in res.reasons[0]


def test_financial_evaluate_healthy_parameters_passes():
    req = FinancialEvaluateRequest(
        mold_cost=5000.0,
        sample_cost=500.0,
        moq=1000,
        unit_product_cost=10.0,
        expected_sales_price=35.0,
        shipping_cost_per_unit=5.0,
        monthly_estimated_sales=500,
        target_payback_months=6,
        category_half_life_months=12,
    )
    res = evaluate_financial_risk(req)
    assert res.financial_state == FinancialState.PASSED
    assert not res.circuit_breaker_triggered
    assert res.metrics is not None
    # fixed costs = 5500
    assert res.metrics.fixed_costs == 5500.0
    # unit margin = 35 - 15 = 20
    assert res.metrics.unit_contribution_margin == 20.0
    # gross margin rate = (20 / 35) * 100 = ~57.14%
    assert res.metrics.gross_margin_rate == 57.14
    # monthly net = 500 * 20 = 10000
    # payback = 5500 / 10000 = 0.6 months <= 6
    assert res.metrics.payback_months == 0.6
    # mold cost ratio = (5500 / 1000) / 35 = 15.71% <= 35%
    assert res.metrics.mold_cost_ratio < 35.0
    assert len(res.break_even_timeline) == 19
    assert len(res.sensitivity_matrix) == 25
    assert len(res.alternative_suggestions) == 0


def test_financial_evaluate_negative_margin_triggers_veto():
    req = FinancialEvaluateRequest(
        mold_cost=5000.0,
        sample_cost=500.0,
        moq=1000,
        unit_product_cost=25.0,
        expected_sales_price=20.0,  # lower than variable cost (25 + 5 = 30)
        shipping_cost_per_unit=5.0,
        monthly_estimated_sales=200,
        target_payback_months=6,
        category_half_life_months=12,
    )
    res = evaluate_financial_risk(req)
    assert res.financial_state == FinancialState.VETOED
    assert res.circuit_breaker_triggered
    assert "NEGATIVE_MARGIN" in res.triggered_rules
    assert len(res.alternative_suggestions) > 0


def test_financial_evaluate_excessive_mold_cost_ratio_triggers_veto():
    req = FinancialEvaluateRequest(
        mold_cost=20000.0,
        sample_cost=1000.0,
        moq=500,  # fixed = 21000, amortized = 42/unit > 35% of price(40) = 14
        unit_product_cost=10.0,
        expected_sales_price=40.0,
        shipping_cost_per_unit=5.0,
        monthly_estimated_sales=600,
        target_payback_months=6,
        category_half_life_months=12,
    )
    res = evaluate_financial_risk(req)
    assert res.financial_state == FinancialState.VETOED
    assert res.circuit_breaker_triggered
    assert "MOLD_COST_RATIO_EXCEEDED" in res.triggered_rules
    assert res.metrics is not None
    assert res.metrics.mold_cost_ratio > 35.0


def test_financial_evaluate_long_payback_period_triggers_veto():
    req = FinancialEvaluateRequest(
        mold_cost=12000.0,
        sample_cost=1000.0,
        moq=1000,
        unit_product_cost=15.0,
        expected_sales_price=25.0,
        shipping_cost_per_unit=5.0,
        # unit margin = 5, monthly = 500, payback = 26 months > 6
        monthly_estimated_sales=100,
        target_payback_months=6,
        category_half_life_months=12,
    )
    res = evaluate_financial_risk(req)
    assert res.financial_state == FinancialState.VETOED
    assert res.circuit_breaker_triggered
    assert "PAYBACK_PERIOD_EXCEEDED" in res.triggered_rules


def test_financial_evaluate_budget_exceeded_triggers_veto():
    req = FinancialEvaluateRequest(
        mold_cost=10000.0,
        sample_cost=1000.0,
        moq=2000,
        unit_product_cost=15.0,
        expected_sales_price=45.0,
        shipping_cost_per_unit=5.0,
        monthly_estimated_sales=800,
        target_payback_months=6,
        category_half_life_months=12,
        max_cash_budget=20000.0,  # initial cash = 11000 + 2000 * 20 = 51000 > 20000
    )
    res = evaluate_financial_risk(req)
    assert res.financial_state == FinancialState.VETOED
    assert res.circuit_breaker_triggered
    assert "BUDGET_EXCEEDED" in res.triggered_rules


async def test_financial_api_endpoints(client):
    # 1. Test rules endpoint
    rules_resp = await client.get("/api/v1/financial/rules")
    assert rules_resp.status_code == 200
    rules_body = rules_resp.json()
    assert rules_body["code"] == 0
    assert len(rules_body["data"]["rules"]) == 4

    # 2. Test evaluate endpoint with empty body -> NOT_EVALUATED
    empty_resp = await client.post("/api/v1/financial/evaluate", json={})
    assert empty_resp.status_code == 200
    empty_body = empty_resp.json()
    assert empty_body["code"] == 0
    assert empty_body["data"]["financial_state"] == "NOT_EVALUATED"

    # 3. Test evaluate endpoint with vetoed parameters
    veto_resp = await client.post(
        "/api/v1/financial/evaluate",
        json={
            "mold_cost": 25000.0,
            "sample_cost": 2000.0,
            "moq": 500,
            "unit_product_cost": 20.0,
            "expected_sales_price": 30.0,
            "shipping_cost_per_unit": 8.0,
            "monthly_estimated_sales": 100,
            "target_payback_months": 6,
            "category_half_life_months": 12,
        },
    )
    assert veto_resp.status_code == 200
    veto_body = veto_resp.json()
    assert veto_body["data"]["financial_state"] == "VETOED"
    assert veto_body["data"]["circuit_breaker_triggered"] is True
    assert len(veto_body["data"]["alternative_suggestions"]) > 0
