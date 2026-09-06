"""Deterministic financial rule engine (docs/api.md §9.1, 04-技术方案 §2.4).

The final veto decision is always made by these rules — never by an LLM.
"""

from dataclasses import dataclass, field
from typing import Any

# Approximate monthly FBA fulfillment fees by tier (USD, deterministic table).
FBA_TIER_FEES: list[tuple[float, str]] = [
    (0.45, "Small Standard"),
    (9.0, "Large Standard"),
    (13.6, "Small Oversize"),
    (float("inf"), "Large Oversize"),
]
FBA_TIER_FEE_USD = {
    "Small Standard": 3.50,
    "Large Standard": 6.00,
    "Small Oversize": 10.00,
    "Large Oversize": 25.00,
}

VOLUMETRIC_DIVISOR = 5000


def volumetric_weight_kg(size_cm: list[float]) -> float:
    l, w, h = size_cm
    return round(l * w * h / VOLUMETRIC_DIVISOR, 2)


def fba_tier_for(weight_kg: float) -> str:
    for limit, tier in FBA_TIER_FEES:
        if weight_kg <= limit:
            return tier
    return "Large Oversize"


def fba_tier_fee(tier: str) -> float:
    return FBA_TIER_FEE_USD.get(tier, 25.0)


@dataclass
class FinancialEvaluation:
    vetoed: bool
    veto_reasons: list[str] = field(default_factory=list)
    roi: float = 0.0
    payback_months: float | None = None
    monthly_profit_delta_usd: float = 0.0


class FinancialEngine:
    """Pure deterministic computations, shared by the workflow and the
    side-effect-free `/financial/simulate` endpoint."""

    def monthly_units(self, constraint: dict[str, Any]) -> float:
        return float(constraint.get("monthly_sales_volume", 1000))

    def evaluate_proposal(
        self,
        proposal: dict[str, Any],
        constraint: dict[str, Any],
    ) -> FinancialEvaluation:
        price = float(constraint.get("expected_price_usd", 0) or 0)
        gross_margin = float(constraint.get("current_gross_margin", 0) or 0)
        mold_cost = float(constraint.get("mold_cost_usd", 0) or 0)
        moq = float(constraint.get("moq", 0) or 0)
        lifecycle_days = float(constraint.get("product_lifecycle_days", 365))
        mold_cycle_days = float(proposal.get("mold_cycle_days", 0) or 0)
        mold_required = bool(proposal.get("mold_opening_required", False))
        defect_reduction = float(proposal.get("defect_rate_reduction", 0) or 0)

        reasons: list[str] = []

        # Rule 1: 开模周期 > 90 天 且 品类生命周期 < 180 天 → 强制否决
        if mold_required and mold_cycle_days > 90 and lifecycle_days < 180:
            reasons.append(
                f"预计开模改造周期 {mold_cycle_days:.0f} 天超过 90 天，"
                f"而品类生命周期仅 {lifecycle_days:.0f} 天（<180 天），改款无法回本"
            )

        # Rule 2: 单位改进成本增加额 > 当前毛利额 × 35% 且无法提价 → 强制否决
        # cost_estimation_usd 为含开模费的总投入，单位增量 = (总投入 - 开模费) / MOQ
        unit_margin = price * gross_margin
        recurring_cost = float(proposal.get("cost_estimation_usd", 0) or 0) - (
            mold_cost if mold_required else 0.0
        )
        unit_increase = recurring_cost / moq if moq else 0.0
        if moq and unit_increase > unit_margin * 0.35:
            reasons.append(
                f"单位改进成本增加 {unit_increase:.2f} 美元，"
                f"超过当前毛利额 {unit_margin:.2f} 美元的 35%，且无法提价"
            )

        # Deterministic ROI / payback model:
        # investment = proposal total cost (mold + recurring)
        # monthly benefit = monthly units × defect reduction × unit margin
        investment = float(proposal.get("cost_estimation_usd", 0) or 0)
        monthly_benefit = self.monthly_units(constraint) * defect_reduction * unit_margin
        roi = monthly_benefit * 12 / investment if investment > 0 else 0.0
        payback = investment / monthly_benefit if monthly_benefit > 0 else None

        return FinancialEvaluation(
            vetoed=bool(reasons),
            veto_reasons=reasons,
            roi=round(roi, 2),
            payback_months=round(payback, 1) if payback is not None else None,
            monthly_profit_delta_usd=round(monthly_benefit, 2),
        )

    def simulate(self, params: dict[str, Any]) -> dict[str, Any]:
        """Stateless what-if simulation for POST /financial/simulate."""
        old_size = params.get("package_size_old_cm") or []
        new_size = params.get("package_size_new_cm") or []
        vol_old = volumetric_weight_kg(old_size) if len(old_size) == 3 else 0.0
        vol_new = volumetric_weight_kg(new_size) if len(new_size) == 3 else 0.0
        tier_old = fba_tier_for(vol_old)
        tier_new = fba_tier_for(vol_new)
        saving = round(fba_tier_fee(tier_old) - fba_tier_fee(tier_new), 2)

        moq = float(params.get("moq", 0) or 0)
        unit_increase = float(params.get("unit_cost_increase_usd", 0) or 0)
        mold_cost = float(params.get("mold_cost_usd", 0) or 0)
        proposal = {
            "cost_estimation_usd": mold_cost + moq * unit_increase,
            "mold_opening_required": mold_cost > 0,
            "mold_cycle_days": params.get("mold_cycle_days", 45),
            "defect_rate_reduction": float(
                params.get("expected_return_rate_reduction", 0) or 0
            ),
        }
        evaluation = self.evaluate_proposal(proposal, params)

        # Sensitivity curve: payback vs achieved return-rate reduction.
        curve = []
        for reduction in (0.10, 0.35, 0.60):
            p = {**proposal, "defect_rate_reduction": reduction}
            ev = self.evaluate_proposal(p, params)
            curve.append(
                {
                    "return_rate_reduction": reduction,
                    "payback_months": ev.payback_months,
                }
            )

        fallback_suggestions: list[str] = []
        if evaluation.vetoed:
            fallback_suggestions = [
                "考虑免开模小改（替换材质/增加卡扣），将投资压缩到毛利承受范围内",
                "优先推进包装履约降本（缩小盒规、FBA 降档），无需开模即可回正现金流",
            ]

        return {
            "volumetric_weight_old_kg": vol_old,
            "volumetric_weight_new_kg": vol_new,
            "fba_tier_old": tier_old,
            "fba_tier_new": tier_new,
            "fulfillment_saving_usd_per_unit": saving,
            "monthly_profit_delta_usd": evaluation.monthly_profit_delta_usd,
            "payback_months": evaluation.payback_months,
            "roi": evaluation.roi,
            "veto_status": "VETOED" if evaluation.vetoed else "PASSED",
            "veto_reasons": evaluation.veto_reasons,
            "fallback_suggestions": fallback_suggestions,
            "payback_curve": curve,
        }
