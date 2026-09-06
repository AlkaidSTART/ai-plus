"""Graph tests: compile, node order, skips, veto retry, exceptions."""

import pytest

from agents.nodes import MAX_FINANCIAL_RETRY
from agents.state import ClusterItem
from agents.workflow import build_graph, create_insight_graph, financial_gate_condition
from services.providers import DeterministicProviders

CONSTRAINT_OK = {
    "mold_cost_usd": 8000,
    "moq": 1000,
    "current_gross_margin": 0.32,
    "expected_price_usd": 29.99,
    "unit_cost_increase_usd": 1.8,
}
# 单位成本远超毛利额 35% → 首轮必然 VETO
CONSTRAINT_VETO = {
    "mold_cost_usd": 0,
    "moq": 1000,
    "current_gross_margin": 0.32,
    "expected_price_usd": 29.99,
    "unit_cost_increase_usd": 1.8 * 1000 * 100,
}


def base_state(**overrides):
    state = {
        "task_id": "tsk_test",
        "asin": "B0C1234ABC",
        "platform": "amazon",
        "marketplace": "US",
        "review_window_months": 6,
        "max_reviews": 40,
        "financial_constraint": CONSTRAINT_OK,
        "options": {},
        "retry_count": 0,
        "veto_status": "PENDING",
        "progress": 0,
    }
    state.update(overrides)
    return state


async def collect(graph, state):
    order = []
    async for chunk in graph.astream(state, stream_mode="updates"):
        order.extend(chunk.keys())
    return order


async def test_graph_compiles():
    graph = create_insight_graph()
    assert graph is not None


async def test_normal_path_reaches_end():
    graph = create_insight_graph()
    order = await collect(graph, base_state())
    expected = [
        "fetch_reviews",
        "vision_audit",
        "semantic_cluster",
        "dual_track_decision",
        "financial_veto",
        "evidence_trace",
        "backtest_eval",
        "finalize",
    ]
    assert order == expected


async def test_vision_skip():
    graph = create_insight_graph()
    state = base_state(options={"enable_vision_audit": False})
    result = await graph.ainvoke(state)
    assert result["visual_evidences"] == []
    # backtest defaults off too
    assert result["backtest_score"] is None


async def test_backtest_enabled():
    graph = create_insight_graph()
    result = await graph.ainvoke(base_state(options={"enable_backtest": True}))
    assert result["backtest_score"] == 0.78


async def test_financial_passed():
    graph = create_insight_graph()
    result = await graph.ainvoke(base_state())
    assert result["veto_status"] == "PASSED"
    assert all(p["status"] == "PASSED" for p in result["proposals"])
    assert result["retry_count"] == 0


async def test_financial_veto_then_fallback_passes():
    graph = create_insight_graph()
    state = base_state(financial_constraint=CONSTRAINT_VETO)
    order = await collect(graph, state)
    # 首轮 VETO 打回一次；降级方案成本极低，第二轮 PASSED
    assert order.count("dual_track_decision") == 2
    assert order.count("financial_veto") == 2
    result = await graph.ainvoke(state)
    assert result["retry_count"] == 1
    assert result["veto_status"] == "PASSED"
    assert all(p["fallback_applied"] for p in result["proposals"])
    assert all(p["status"] == "PASSED" for p in result["proposals"])


async def test_financial_retry_exhausted_proceeds_with_veto():
    class AlwaysVetoDecision(DeterministicProviders):
        pass

    providers = DeterministicProviders()
    original = providers.decision.decide

    async def always_veto(task_id, clusters, constraint, retry_count):
        proposals = await original(task_id, clusters, constraint, retry_count)
        for p in proposals:
            # 即便是降级方案也违反否决规则（单位成本超过毛利额 35%）
            p["cost_estimation_usd"] = 5_000_000
        return proposals

    providers.decision.decide = always_veto
    graph = build_graph(providers)
    state = base_state(financial_constraint=CONSTRAINT_VETO)
    order = await collect(graph, state)

    assert order.count("dual_track_decision") == 1 + MAX_FINANCIAL_RETRY
    assert order.count("financial_veto") == 1 + MAX_FINANCIAL_RETRY
    assert order[-1] == "finalize"
    result = await graph.ainvoke(state)
    assert result["retry_count"] == MAX_FINANCIAL_RETRY
    assert result["veto_status"] == "VETOED"
    assert all(p["status"] == "VETOED" and p["veto_reason"] for p in result["proposals"])


async def test_node_exception_fails():
    providers = DeterministicProviders()

    async def boom(*args, **kwargs):
        raise RuntimeError("upstream exploded")

    providers.reviews.fetch = boom
    graph = build_graph(providers)
    with pytest.raises(RuntimeError, match="upstream exploded"):
        await graph.ainvoke(base_state())


async def test_final_report_shape():
    graph = create_insight_graph()
    result = await graph.ainvoke(base_state())
    report = result["final_report"]
    assert report["task_id"] == "tsk_test"
    summary = report["summary"]
    assert summary["review_count"] == len(result["raw_reviews"])
    assert summary["cluster_count"] == len(result["clustered_issues"])
    assert summary["proposal_count"] == len(result["proposals"])
    assert summary["veto_status"] == "PASSED"


async def test_evidence_links_reference_real_clusters():
    graph = create_insight_graph()
    result = await graph.ainvoke(base_state())
    cluster_ids = {c["cluster_id"] for c in result["clustered_issues"]}
    review_ids = {r["review_id"] for r in result["raw_reviews"]}
    for link in result["evidence_links"]:
        assert link["cluster_id"] in cluster_ids
        assert set(link["review_ids"]) <= review_ids


async def test_gate_condition():
    assert financial_gate_condition({"veto_status": "VETOED", "retry_count": 0}) == "retry_decision"
    assert financial_gate_condition({"veto_status": "VETOED", "retry_count": 2}) == "proceed_trace"
    assert financial_gate_condition({"veto_status": "PASSED", "retry_count": 0}) == "proceed_trace"
