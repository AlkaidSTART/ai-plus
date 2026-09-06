"""LangGraph node implementations.

Each node follows the same contract: read state → call a service/provider →
return a partial state update. No HTTP / SQL / SDK / Redis access here.
"""

from typing import Any

from agents.state import InsightState
from services.providers import DeterministicProviders

# Node -> (SSE step, progress low, progress high) — docs/api.md §4.3
STEP_BY_NODE: dict[str, tuple[str, int, int]] = {
    "fetch_reviews": ("FETCHING_DATA", 5, 25),
    "vision_audit": ("VISION_AUDIT", 25, 45),
    "semantic_cluster": ("SEMANTIC_CLUSTER", 45, 65),
    "dual_track_decision": ("DUAL_DECISION", 65, 85),
    "financial_veto": ("FINANCIAL_VETO", 85, 92),
    "evidence_trace": ("EVIDENCE_TRACE", 92, 96),
    "backtest_eval": ("BACKTEST_EVAL", 96, 99),
    "finalize": ("COMPLETED", 100, 100),
}

NODE_MESSAGES: dict[str, str] = {
    "fetch_reviews": "采集并清洗评论数据",
    "vision_audit": "买家实拍图取证",
    "semantic_cluster": "多语言语义聚类",
    "dual_track_decision": "生成双栏改款建议",
    "financial_veto": "财务否决审核",
    "evidence_trace": "证据链反向索引校验",
    "backtest_eval": "历史切片回测",
    "finalize": "汇总最终报告",
}

MAX_FINANCIAL_RETRY = 2


def _options(state: InsightState) -> dict[str, Any]:
    return state.get("options") or {}


def build_nodes(providers: DeterministicProviders | None = None) -> dict[str, Any]:
    providers = providers or DeterministicProviders()

    async def fetch_reviews(state: InsightState) -> dict[str, Any]:
        reviews = await providers.reviews.fetch(
            state["asin"],
            state.get("marketplace", "US"),
            state.get("review_window_months", 6),
            state.get("max_reviews", 500),
        )
        return {
            "raw_reviews": reviews,
            "current_node": "fetch_reviews",
            "progress": STEP_BY_NODE["fetch_reviews"][2],
        }

    async def vision_audit(state: InsightState) -> dict[str, Any]:
        if not _options(state).get("enable_vision_audit", True):
            return {
                "visual_evidences": [],
                "current_node": "vision_audit",
                "progress": STEP_BY_NODE["vision_audit"][2],
            }
        evidences = await providers.vision.audit(state.get("raw_reviews", []))
        return {
            "visual_evidences": evidences,
            "current_node": "vision_audit",
            "progress": STEP_BY_NODE["vision_audit"][2],
        }

    async def semantic_cluster(state: InsightState) -> dict[str, Any]:
        clusters = await providers.cluster.cluster(
            state["task_id"],
            state.get("raw_reviews", []),
            state.get("visual_evidences", []),
        )
        return {
            "clustered_issues": clusters,
            "current_node": "semantic_cluster",
            "progress": STEP_BY_NODE["semantic_cluster"][2],
        }

    async def dual_track_decision(state: InsightState) -> dict[str, Any]:
        # Being routed back by financial_veto means this is a retry round.
        is_retry = state.get("veto_status") == "VETOED"
        retry_count = state.get("retry_count", 0) + (1 if is_retry else 0)
        proposals = await providers.decision.decide(
            state["task_id"],
            state.get("clustered_issues", []),
            state.get("financial_constraint", {}),
            retry_count,
        )
        return {
            "proposals": proposals,
            "fallback_applied": retry_count > 0,
            "retry_count": retry_count,
            "current_node": "dual_track_decision",
            "progress": STEP_BY_NODE["dual_track_decision"][2],
        }

    async def financial_veto(state: InsightState) -> dict[str, Any]:
        constraint = state.get("financial_constraint", {})
        proposals = state.get("proposals", [])
        any_vetoed = False
        for proposal in proposals:
            evaluation = providers.financial.evaluate_proposal(proposal, constraint)
            if evaluation.vetoed:
                any_vetoed = True
                proposal["status"] = "VETOED"
                proposal["veto_reason"] = "；".join(evaluation.veto_reasons)
            else:
                proposal["status"] = "PASSED"
                proposal["veto_reason"] = None
                proposal["estimated_roi"] = evaluation.roi

        await providers.financial.record(
            state["task_id"], proposals, constraint, state.get("retry_count", 0)
        )
        return {
            "proposals": proposals,
            "veto_status": "VETOED" if any_vetoed else "PASSED",
            "retry_count": state.get("retry_count", 0),
            "current_node": "financial_veto",
            "progress": STEP_BY_NODE["financial_veto"][2],
        }

    async def evidence_trace(state: InsightState) -> dict[str, Any]:
        links = await providers.evidence.trace(
            state["task_id"],
            state.get("proposals", []),
            state.get("clustered_issues", []),
            state.get("visual_evidences", []),
        )
        return {
            "evidence_links": links,
            "current_node": "evidence_trace",
            "progress": STEP_BY_NODE["evidence_trace"][2],
        }

    async def backtest_eval(state: InsightState) -> dict[str, Any]:
        if not _options(state).get("enable_backtest", False):
            return {
                "backtest_score": None,
                "current_node": "backtest_eval",
                "progress": STEP_BY_NODE["backtest_eval"][2],
            }
        raise RuntimeError(
            "P2 历史回测（Backtest）尚未实现：无法执行 enable_backtest=true 的任务，"
            "请使用 enable_backtest=false 创建任务"
        )

    async def finalize(state: InsightState) -> dict[str, Any]:
        clusters = state.get("clustered_issues", [])
        proposals = state.get("proposals", [])
        reviews = state.get("raw_reviews", [])
        ratings = [r["rating"] for r in reviews]
        avg_rating = round(sum(ratings) / len(ratings), 2) if ratings else None
        negative = [r for r in reviews if r["rating"] <= 3.0]
        negative_rate = round(len(negative) / len(reviews), 2) if reviews else None
        summary = {
            "review_count": len(reviews),
            "cluster_count": len(clusters),
            "proposal_count": len(proposals),
            "veto_status": state.get("veto_status", "PENDING"),
            "backtest_score": state.get("backtest_score"),
            "avg_rating": avg_rating,
            "negative_review_rate": negative_rate,
        }
        final_report = {
            "task_id": state["task_id"],
            "summary": summary,
            "clusters": clusters,
            "proposals": proposals,
            "evidence_links": state.get("evidence_links", []),
            "visual_evidences": state.get("visual_evidences", []),
        }
        return {
            "final_report": final_report,
            "current_node": "finalize",
            "progress": STEP_BY_NODE["finalize"][1],
        }

    return {
        "fetch_reviews": fetch_reviews,
        "vision_audit": vision_audit,
        "semantic_cluster": semantic_cluster,
        "dual_track_decision": dual_track_decision,
        "financial_veto": financial_veto,
        "evidence_trace": evidence_trace,
        "backtest_eval": backtest_eval,
        "finalize": finalize,
    }
