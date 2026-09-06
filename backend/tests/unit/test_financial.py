"""Financial rule engine tests (docs/api.md §9.1)."""

from services.financial import FinancialEngine, fba_tier_for, volumetric_weight_kg

ENGINE = FinancialEngine()

BASE_CONSTRAINT = {
    "mold_cost_usd": 8000,
    "moq": 1000,
    "current_gross_margin": 0.32,
    "expected_price_usd": 29.99,
    "monthly_sales_volume": 1000,
}


def proposal(**overrides):
    base = {
        "cost_estimation_usd": 8500,
        "mold_opening_required": True,
        "mold_cycle_days": 45,
        "defect_rate_reduction": 0.6,
    }
    base.update(overrides)
    return base


def test_normal_proposal_passes():
    result = ENGINE.evaluate_proposal(proposal(), BASE_CONSTRAINT)
    assert not result.vetoed
    assert result.roi > 0
    assert result.payback_months is not None


def test_mold_cycle_over_90_with_short_lifecycle_vetoes():
    result = ENGINE.evaluate_proposal(
        proposal(mold_cycle_days=120),
        {**BASE_CONSTRAINT, "product_lifecycle_days": 120},
    )
    assert result.vetoed
    assert any("90 天" in r for r in result.veto_reasons)


def test_mold_cycle_over_90_with_long_lifecycle_passes():
    result = ENGINE.evaluate_proposal(
        proposal(mold_cycle_days=120),
        {**BASE_CONSTRAINT, "product_lifecycle_days": 365},
    )
    assert not result.vetoed


def test_unit_cost_over_margin_35pct_vetoes():
    # 单位成本 = (8500 - 8000) / 100 = 5.0 > 29.99*0.32*0.35 ≈ 3.36
    result = ENGINE.evaluate_proposal(proposal(), {**BASE_CONSTRAINT, "moq": 100})
    assert result.vetoed
    assert any("35%" in r for r in result.veto_reasons)


def test_no_mold_no_mold_veto():
    result = ENGINE.evaluate_proposal(
        proposal(mold_opening_required=False, mold_cycle_days=0, cost_estimation_usd=500),
        {**BASE_CONSTRAINT, "product_lifecycle_days": 30},
    )
    assert not result.vetoed


def test_volumetric_weight_and_tiers():
    assert volumetric_weight_kg([30, 20, 12]) == 1.44
    assert volumetric_weight_kg([26, 18, 9]) == 0.84
    assert fba_tier_for(0.4) == "Small Standard"
    assert fba_tier_for(1.44) == "Large Standard"
    assert fba_tier_for(20.0) == "Large Oversize"


def test_simulate_stateless_shape():
    result = ENGINE.simulate(
        {
            "mold_cost_usd": 8000,
            "moq": 1000,
            "current_gross_margin": 0.32,
            "expected_price_usd": 29.99,
            "unit_cost_increase_usd": 1.8,
            "package_size_old_cm": [30, 20, 12],
            "package_size_new_cm": [26, 18, 9],
            "expected_return_rate_reduction": 0.35,
        }
    )
    assert result["fba_tier_old"] == "Large Standard"
    assert result["fba_tier_new"] == "Large Standard"  # 0.84kg 仍是 Large Standard
    assert result["fulfillment_saving_usd_per_unit"] == 0.0
    assert len(result["payback_curve"]) == 3
    assert result["veto_status"] in {"PASSED", "VETOED"}


def test_simulate_veto_has_fallback_suggestions():
    result = ENGINE.simulate(
        {
            "mold_cost_usd": 8000,
            "moq": 10,  # 单位成本极高 → 否决
            "current_gross_margin": 0.32,
            "expected_price_usd": 29.99,
            "unit_cost_increase_usd": 100,
            "expected_return_rate_reduction": 0.35,
        }
    )
    assert result["veto_status"] == "VETOED"
    assert result["veto_reasons"]
    assert result["fallback_suggestions"]
