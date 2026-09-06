"""Read workflow results for API serving.

Results are read from the task's `final_report` (persisted by the runtime to
the task row — PostgreSQL JSONB in production), so serving works uniformly in
memory-demo mode and DB production mode.
"""

from typing import Any

from runtime.task_store import TaskRecord, TaskStatus


def final_report(task: TaskRecord) -> dict[str, Any] | None:
    return task.final_report


def clusters_of(task: TaskRecord) -> list[dict[str, Any]]:
    return list((task.final_report or {}).get("clusters", []))


def proposals_of(task: TaskRecord) -> list[dict[str, Any]]:
    return list((task.final_report or {}).get("proposals", []))


def evidences_of(task: TaskRecord) -> list[dict[str, Any]]:
    return list((task.final_report or {}).get("visual_evidences", []))


def financial_of(task: TaskRecord) -> dict[str, Any] | None:
    proposals = proposals_of(task)
    if not proposals:
        return None
    vetoed = [p for p in proposals if p.get("status") == "VETOED"]
    reasons = [p["veto_reason"] for p in vetoed if p.get("veto_reason")]
    return {
        "task_id": task.task_id,
        "veto_status": "VETOED" if vetoed else "PASSED",
        "checked_proposals": len(proposals),
        "vetoed_proposal_ids": [p["proposal_id"] for p in vetoed],
        "veto_reasons": reasons,
        "fallback_applied": task.retry_count > 0,
        "retry_count": task.retry_count,
        "financial_constraint": task.financial_constraint,
    }


def require_completed(task: TaskRecord) -> dict[str, Any]:
    if task.status != TaskStatus.COMPLETED:
        from api.errors import ApiError, ErrorCode

        raise ApiError(
            ErrorCode.CONFLICT, f"任务尚未完成（当前状态 {task.status.value}），结果不可用"
        )
    return task.final_report or {}
