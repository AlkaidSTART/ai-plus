"""Deterministic financial risk evaluation and circuit breaker service."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from insightx.models import Report, Task, TaskItem, utc_now
from insightx.schemas import (
    AlternativeSuggestion,
    BreakEvenPoint,
    FinancialEvaluateRequest,
    FinancialEvaluateResponse,
    FinancialMetrics,
    FinancialRuleInfo,
    FinancialRuleItem,
    FinancialState,
    SensitivityPoint,
)

CURRENT_RULE_VERSION = "financial_rules_v1.0"

RULES_METADATA = [
    FinancialRuleItem(
        code="NEGATIVE_MARGIN",
        name="边际贡献为负/零熔断",
        description="预期售价低于或等于单件变动成本（采购成本+海运履约），销售产生结构性亏损。",
        threshold="单件边际贡献 <= 0",
    ),
    FinancialRuleItem(
        code="MOLD_COST_RATIO_EXCEEDED",
        name="模具固定成本分摊超标熔断",
        description="单件分摊开模打样成本占售价比重过高，严重压缩利润空间并放大滞销风险。",
        threshold="首批单件分摊开模打样成本 > 预期售价 * 35%",
    ),
    FinancialRuleItem(
        code="PAYBACK_PERIOD_EXCEEDED",
        name="回本周期超期熔断",
        description="预估静态回本周期超过期望回本上限或品类生命周期半衰期，资金沉淀过久。",
        threshold="预估回本月数 > min(期望回本月数, 品类半衰期)",
    ),
    FinancialRuleItem(
        code="BUDGET_EXCEEDED",
        name="启动资金超限熔断",
        description="开模、打样与首批生产履约所需的总初始资金超过设定的资金预算上限。",
        threshold="首批启动资金需求 > 最大启动资金预算",
    ),
]


def get_financial_rules() -> FinancialRuleInfo:
    """Return active deterministic financial veto rules."""
    return FinancialRuleInfo(
        rule_version=CURRENT_RULE_VERSION,
        rules=RULES_METADATA,
    )


def evaluate_financial_risk(
    request: FinancialEvaluateRequest,
    *,
    session: Session | None = None,
    tenant_id: str | None = None,
) -> FinancialEvaluateResponse:
    """Evaluate financial viability and circuit breakers using deterministic rules."""
    # ponytail: 静态回本与线性销量测算；后续接入动态蒙特卡洛敏感度分布模拟
    critical_inputs = [
        request.mold_cost,
        request.sample_cost,
        request.moq,
        request.unit_product_cost,
        request.expected_sales_price,
        request.shipping_cost_per_unit,
        request.monthly_estimated_sales,
    ]

    assumptions: dict[str, Any] = {
        "currency": request.currency,
        "target_payback_months": request.target_payback_months,
        "category_half_life_months": request.category_half_life_months,
        "max_cash_budget": request.max_cash_budget,
    }

    # 1. 缺失关键输入时恒为 NOT_EVALUATED
    if any(v is None for v in critical_inputs):
        return FinancialEvaluateResponse(
            financial_state=FinancialState.NOT_EVALUATED,
            circuit_breaker_triggered=False,
            rule_version=request.rule_version,
            currency=request.currency,
            evaluated_at=utc_now(),
            reasons=[
                "缺失开模预算、MOQ、单位采购成本或预估售价等关键输入，"
                "财务处于未评估状态（NOT_EVALUATED），不等于通过或 0 收益。"
            ],
            triggered_rules=[],
            metrics=None,
            break_even_timeline=[],
            sensitivity_matrix=[],
            alternative_suggestions=[],
            applied_assumptions=assumptions,
        )

    mold_cost = float(request.mold_cost or 0.0)
    sample_cost = float(request.sample_cost or 0.0)
    moq = int(request.moq or 0)
    unit_product_cost = float(request.unit_product_cost or 0.0)
    expected_sales_price = float(request.expected_sales_price or 0.0)
    shipping_cost_per_unit = float(request.shipping_cost_per_unit or 0.0)
    monthly_sales = int(request.monthly_estimated_sales or 0)
    target_payback = int(request.target_payback_months)
    half_life = int(request.category_half_life_months)

    # 2. 确定性公式计算
    fixed_costs = round(mold_cost + sample_cost, 2)
    variable_cost_per_unit = round(unit_product_cost + shipping_cost_per_unit, 2)
    unit_margin = round(expected_sales_price - variable_cost_per_unit, 2)
    gross_margin_rate = (
        round((unit_margin / expected_sales_price) * 100, 2)
        if expected_sales_price > 0
        else 0.0
    )
    initial_batch_cash = round(fixed_costs + (moq * variable_cost_per_unit), 2)
    amortized_mold = round(fixed_costs / moq, 2) if moq > 0 else 0.0
    mold_cost_ratio = (
        round((amortized_mold / expected_sales_price) * 100, 2)
        if expected_sales_price > 0
        else 0.0
    )
    monthly_contribution = round(monthly_sales * unit_margin, 2)

    if unit_margin > 0 and monthly_contribution > 0:
        break_even_units = int(fixed_costs / unit_margin + 0.9999)
        payback_months = round(fixed_costs / monthly_contribution, 1)
    else:
        break_even_units = None
        payback_months = 999.0

    if initial_batch_cash > 0:
        annual_profit = (monthly_contribution * 12) - fixed_costs
        estimated_12m_roi = round((annual_profit / initial_batch_cash) * 100, 1)
    else:
        estimated_12m_roi = 0.0

    metrics = FinancialMetrics(
        fixed_costs=fixed_costs,
        variable_cost_per_unit=variable_cost_per_unit,
        unit_contribution_margin=unit_margin,
        gross_margin_rate=gross_margin_rate,
        initial_batch_cash=initial_batch_cash,
        amortized_mold_cost_per_unit=amortized_mold,
        mold_cost_ratio=mold_cost_ratio,
        monthly_contribution=monthly_contribution,
        break_even_units=break_even_units,
        payback_months=payback_months,
        estimated_12m_roi=estimated_12m_roi,
    )

    # 3. 熔断裁决校验
    triggered_rules: list[str] = []
    reasons: list[str] = []

    # Rule 1: NEGATIVE_MARGIN
    if unit_margin <= 0:
        triggered_rules.append("NEGATIVE_MARGIN")
        reasons.append(
            f"负边际贡献熔断：单件售价(${expected_sales_price:.2f})无法覆盖采购履约成本(${variable_cost_per_unit:.2f})，"
            f"单件贡献为 ${unit_margin:.2f} <= $0，销售产生结构性亏损，无法收回固定投入。"
        )

    # Rule 2: MOLD_COST_RATIO_EXCEEDED
    if expected_sales_price > 0 and mold_cost_ratio > 35.0:
        triggered_rules.append("MOLD_COST_RATIO_EXCEEDED")
        reasons.append(
            f"开模固定成本分摊超标熔断：单件分摊模具成本(${amortized_mold:.2f})占预期售价(${expected_sales_price:.2f})的 {mold_cost_ratio:.1f}%，"
            f"超出 35.0% 警戒上限，沉没成本过重侵蚀抗风险空间。"
        )

    # Rule 3: PAYBACK_PERIOD_EXCEEDED
    effective_limit = min(target_payback, half_life)
    if payback_months > effective_limit:
        triggered_rules.append("PAYBACK_PERIOD_EXCEEDED")
        limit_desc = "期望上限" if effective_limit == target_payback else "品类半衰期"
        reasons.append(
            f"回本周期超期熔断：预估静态回本周期({payback_months:.1f} 个月)超出{limit_desc}({effective_limit} 个月)，"
            f"资金周转过慢，存在竞品迭代淘汰与压仓滞销风险。"
        )

    # Rule 4: BUDGET_EXCEEDED
    if request.max_cash_budget is not None and initial_batch_cash > request.max_cash_budget:
        triggered_rules.append("BUDGET_EXCEEDED")
        reasons.append(
            f"启动资金预算超限熔断：首批启动资金需求(${initial_batch_cash:,.2f})超过设定预算门槛(${request.max_cash_budget:,.2f})。"
        )

    # 4. 状态与替代方案生成
    if triggered_rules:
        financial_state = FinancialState.VETOED
        circuit_breaker = True
        suggestions = [
            AlternativeSuggestion(
                suggestion_id="alt_no_mold",
                title="方案一：免开模小改（公模微调/换色定制）",
                description=(
                    f"放弃新开高额私模（当前开模费 ${mold_cost:,.2f}），改用成熟公模基础件，"
                    "通过激光镭雕、喷涂换色或模块化通用配件实现改款微创新。开模费用降为 0。"
                ),
                estimated_impact=f"免除 ${mold_cost:,.2f} 开模投入，显著缩短回本周期并降低资金敞口。",
                suggested_params={"mold_cost": 0.0, "sample_cost": min(sample_cost, 400.0)},
            ),
            AlternativeSuggestion(
                suggestion_id="alt_packaging",
                title="方案二：包装轻量化与履约折叠（降低单件运费）",
                description=(
                    f"针对单件海运与履约运费 ${shipping_cost_per_unit:.2f}，重新设计结构件与折叠彩盒，"
                    "消除抛重体积冗余，争取海运运费下调 30%。"
                ),
                estimated_impact=(
                    f"预计单件运费降至 ${shipping_cost_per_unit * 0.7:.2f}，"
                    f"单件边际贡献直接增厚 ${shipping_cost_per_unit * 0.3:.2f}。"
                ),
                suggested_params={
                    "shipping_cost_per_unit": round(shipping_cost_per_unit * 0.7, 2)
                },
            ),
            AlternativeSuggestion(
                suggestion_id="alt_lower_moq",
                title="方案三：阶梯小批量试产（调低初始 MOQ）",
                description=(
                    f"与工厂协商首批起订量从 {moq} 件降至 {max(200, int(moq * 0.5))} 件，"
                    "先行投放小批量试水验证转化率与差评修复度，验证成功后再追加订单。"
                ),
                estimated_impact=(
                    f"首批生产投入资金降低约 "
                    f"${(moq - max(200, int(moq * 0.5))) * variable_cost_per_unit:,.2f}，控制滞销压仓敞口。"
                ),
                suggested_params={"moq": max(200, int(moq * 0.5))},
            ),
        ]
    else:
        financial_state = FinancialState.PASSED
        circuit_breaker = False
        reasons = [
            f"各项财务风控指标均在安全阈值以内：单位边际贡献 ${unit_margin:.2f}（毛利率 {gross_margin_rate:.1f}%），"
            f"预估回本周期 {payback_months:.1f} 个月（≤ 门槛 {effective_limit} 个月），"
            f"单件模具分摊占比 {mold_cost_ratio:.1f}%（≤ 35.0%）。"
            "商业可行性满足立项准入标准（不等于保证市场商业成功）。"
        ]
        suggestions = []

    # 5. 动态盈亏平衡走势数据（0 到 18 个月）
    timeline: list[BreakEvenPoint] = []
    for m in range(19):
        cum_units = monthly_sales * m
        cum_rev = round(cum_units * expected_sales_price, 2)
        cum_cost = round(fixed_costs + (cum_units * variable_cost_per_unit), 2)
        net_cash = round(cum_rev - cum_cost, 2)
        timeline.append(
            BreakEvenPoint(
                month=m,
                cumulative_units=cum_units,
                cumulative_revenue=cum_rev,
                cumulative_cost=cum_cost,
                net_cashflow=net_cash,
                is_break_even=(net_cash >= 0 and m > 0),
            )
        )

    # 6. 销量与售价敏感度矩阵
    sensitivity: list[SensitivityPoint] = []
    sales_deltas = [-0.30, -0.15, 0.0, 0.15, 0.30]
    price_deltas = [-0.15, -0.10, 0.0, 0.10, 0.15]
    for s_delta in sales_deltas:
        sim_sales = max(1, int(monthly_sales * (1.0 + s_delta)))
        for p_delta in price_deltas:
            sim_price = round(expected_sales_price * (1.0 + p_delta), 2)
            sim_margin = sim_price - variable_cost_per_unit
            if sim_margin <= 0:
                sim_payback = 999.0
                sim_vetoed = True
            else:
                sim_monthly_net = sim_sales * sim_margin
                sim_payback = round(fixed_costs / sim_monthly_net, 1)
                sim_vetoed = sim_payback > effective_limit
            sensitivity.append(
                SensitivityPoint(
                    sales_change_percent=round(s_delta * 100, 1),
                    price_change_percent=round(p_delta * 100, 1),
                    payback_months=sim_payback,
                    is_vetoed=sim_vetoed,
                )
            )

    # 7. 可选同步到已存在的报告
    if session is not None and request.task_id and request.item_id:
        query = select(Report).where(
            Report.task_id == request.task_id,
            Report.item_id == request.item_id,
        )
        if tenant_id:
            query = query.where(Report.tenant_id == tenant_id)
        report = session.scalar(query)
        if report is not None:
            report.financial_state = financial_state.value
            meta = dict(report.model_metadata or {})
            meta["financial_evaluation"] = {
                "financial_state": financial_state.value,
                "circuit_breaker_triggered": circuit_breaker,
                "evaluated_at": utc_now().isoformat(),
                "rule_version": request.rule_version,
                "metrics": metrics.model_dump(),
                "triggered_rules": triggered_rules,
                "reasons": reasons,
            }
            report.model_metadata = meta
            session.commit()

    return FinancialEvaluateResponse(
        financial_state=financial_state,
        circuit_breaker_triggered=circuit_breaker,
        rule_version=request.rule_version,
        currency=request.currency,
        evaluated_at=utc_now(),
        reasons=reasons,
        triggered_rules=triggered_rules,
        metrics=metrics,
        break_even_timeline=timeline,
        sensitivity_matrix=sensitivity,
        alternative_suggestions=suggestions,
        applied_assumptions=assumptions,
    )


def get_task_item_financial(
    session: Session,
    *,
    tenant_id: str,
    task_id: str,
    item_id: str,
) -> FinancialEvaluateResponse:
    """Retrieve existing financial evaluation for a task item or return default NOT_EVALUATED."""
    report = session.scalar(
        select(Report).where(
            Report.tenant_id == tenant_id,
            Report.task_id == task_id,
            Report.item_id == item_id,
        )
    )
    if report is not None and "financial_evaluation" in (report.model_metadata or {}):
        eval_data = report.model_metadata["financial_evaluation"]
        # If stored, build quick response with saved state
        state = FinancialState(report.financial_state)
        return FinancialEvaluateResponse(
            financial_state=state,
            circuit_breaker_triggered=eval_data.get("circuit_breaker_triggered", False),
            rule_version=eval_data.get("rule_version", CURRENT_RULE_VERSION),
            currency="USD",
            evaluated_at=utc_now(),
            reasons=eval_data.get("reasons", []),
            triggered_rules=eval_data.get("triggered_rules", []),
            metrics=(
                FinancialMetrics.model_validate(eval_data["metrics"])
                if eval_data.get("metrics")
                else None
            ),
            break_even_timeline=[],
            sensitivity_matrix=[],
            alternative_suggestions=[],
            applied_assumptions={},
        )

    # Otherwise return default NOT_EVALUATED
    return evaluate_financial_risk(FinancialEvaluateRequest())
