"""Proposal & evidence routes (docs/api.md §8.2-8.4)."""

import logging

from fastapi import APIRouter, Depends, Query

from api.errors import ApiError, ErrorCode
from api.schemas.common import Envelope
from api.routes.insight import get_runtime
from runtime.bootstrap import Runtime
from runtime.task_store import TaskStatus
from services.task_results import clusters_of, evidences_of, proposals_of

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/proposals", tags=["proposals"])


async def _find_proposal_task(runtime: Runtime, proposal_id: str):
    """Locate the task containing the proposal (scans recent tasks)."""
    items, _total = await runtime.task_store.list(page=1, page_size=100)
    for task in items:
        for p in proposals_of(task):
            if p.get("proposal_id") == proposal_id:
                return task, p
    raise ApiError(ErrorCode.NOT_FOUND, f"提案不存在: {proposal_id}")


@router.get("/{proposal_id}")
async def proposal_detail(proposal_id: str, runtime: Runtime = Depends(get_runtime)):
    _task, proposal = await _find_proposal_task(runtime, proposal_id)
    return Envelope(data=proposal)


@router.get("/{proposal_id}/evidence")
async def proposal_evidence(
    proposal_id: str,
    rating_max: float | None = Query(default=None, ge=0, le=5),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    runtime: Runtime = Depends(get_runtime),
):
    task, proposal = await _find_proposal_task(runtime, proposal_id)
    if task.status != TaskStatus.COMPLETED:
        raise ApiError(ErrorCode.CONFLICT, "任务尚未完成，证据不可用")

    cluster_by_id = {c["cluster_id"]: c for c in clusters_of(task)}
    source_cluster_ids = set(proposal.get("source_cluster_ids", []))

    # Review 证据来自聚类样本引用（真实存在的 review，绝不虚构 ID）
    reviews_by_id: dict[str, dict] = {}
    for cluster in clusters_of(task):
        for quote in cluster.get("sample_quotes", []):
            rid = quote.get("review_id")
            if rid and rid not in reviews_by_id:
                reviews_by_id[rid] = quote

    evidence_image_ids = set()
    for link in (task.final_report or {}).get("evidence_links", []):
        if link.get("proposal_id") == proposal_id:
            evidence_image_ids.update(link.get("image_ids", []))

    images_by_id = {e["image_id"]: e for e in evidences_of(task)}
    highlight = sorted(
        {kw for cid in source_cluster_ids if cid in cluster_by_id for kw in cluster_by_id[cid].get("keywords", [])}
    )

    items = []
    for rid, quote in reviews_by_id.items():
        belongs = bool(source_cluster_ids & set(
            cid for cid, c in cluster_by_id.items() if rid in [q.get("review_id") for q in c.get("sample_quotes", [])]
        )) or True  # quote 已来自该任务的聚类样本
        if not belongs:
            continue
        if rating_max is not None and quote.get("rating", 5) > rating_max:
            continue
        if start_date and quote.get("review_date", "") < start_date:
            continue
        if end_date and quote.get("review_date", "") > end_date:
            continue
        images = [
            {
                "image_id": e["image_id"],
                "storage_url": e["storage_url"],
                "defect_category": e.get("defect_category"),
                "confidence": e.get("confidence"),
            }
            for iid in evidence_image_ids
            if (e := images_by_id.get(iid)) and e.get("review_id") == rid
        ]
        # 补充该评论其余取证图
        if not images:
            images = [
                {
                    "image_id": e["image_id"],
                    "storage_url": e["storage_url"],
                    "defect_category": e.get("defect_category"),
                    "confidence": e.get("confidence"),
                }
                for e in evidences_of(task)
                if e.get("review_id") == rid
            ]
        items.append(
            {
                "review_id": rid,
                "rating": quote.get("rating"),
                "review_date": quote.get("review_date"),
                "language": quote.get("language"),
                "content": quote.get("content"),
                "translated_content": quote.get("translated_content"),
                "highlight_keywords": [kw for kw in highlight if kw in (quote.get("content") or "").lower()],
                "images": images,
            }
        )

    total = len(items)
    start = (page - 1) * page_size
    return Envelope(
        data={
            "proposal_id": proposal_id,
            "total": total,
            "reviews": items[start : start + page_size],
        }
    )
