"""LangGraph state machine wiring.

START → fetch_reviews → vision_audit → semantic_cluster → dual_track_decision
      → financial_veto ─(VETO & retry_count < 2)→ dual_track_decision
                       ─(PASS / retry exhausted)→ evidence_trace
      → backtest_eval → finalize → END
"""

from typing import Any

from langgraph.graph import END, StateGraph

from agents.nodes import MAX_FINANCIAL_RETRY, build_nodes
from agents.state import InsightState
from services.providers import DeterministicProviders


def financial_gate_condition(state: InsightState) -> str:
    if state.get("veto_status") == "VETOED" and state.get("retry_count", 0) < MAX_FINANCIAL_RETRY:
        return "retry_decision"
    return "proceed_trace"


def build_graph(providers: DeterministicProviders | None = None):
    nodes = build_nodes(providers)
    workflow: StateGraph = StateGraph(InsightState)
    for name, fn in nodes.items():
        workflow.add_node(name, fn)

    workflow.set_entry_point("fetch_reviews")
    workflow.add_edge("fetch_reviews", "vision_audit")
    workflow.add_edge("vision_audit", "semantic_cluster")
    workflow.add_edge("semantic_cluster", "dual_track_decision")
    workflow.add_edge("dual_track_decision", "financial_veto")
    workflow.add_conditional_edges(
        "financial_veto",
        financial_gate_condition,
        {
            "retry_decision": "dual_track_decision",
            "proceed_trace": "evidence_trace",
        },
    )
    workflow.add_edge("evidence_trace", "backtest_eval")
    workflow.add_edge("backtest_eval", "finalize")
    workflow.add_edge("finalize", END)
    return workflow.compile()


def create_insight_graph():
    """Default graph wired to the deterministic providers."""
    return build_graph(DeterministicProviders())
