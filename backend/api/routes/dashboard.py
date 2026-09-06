"""Dashboard routes (docs/api.md §5). All KPIs derive from real task data."""

import logging

from fastapi import APIRouter, Depends, Query

from api.errors import ApiError, ErrorCode
from api.schemas.common import Envelope, PageData
from api.schemas.financial import DashboardOverview, RecommendationItem
from api.routes.insight import get_runtime
from runtime.bootstrap import Runtime
from runtime.task_store import TaskStatus
from services.task_results import proposals_of

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

# 聚合扫描上限（MVP 单机规模足够；后续可下推到 SQL）
SCAN_LIMIT = 100
# FBA 节省池口径：包装轨提案的单件履约节省 × 默认月销 1000（口径在代码中固定）
DEFAULT_MONTHLY_VOLUME = 1000


async def _scan_tasks(runtime: Runtime):
    items, _total = await runtime.task_store.list(page=1, page_size=SCAN_LIMIT)
    return items


@router.get("/overview", response_model=Envelope[DashboardOverview])
async def overview(runtime: Runtime = Depends(get_runtime)) -> Envelope[DashboardOverview]:
    tasks = await _scan_tasks(runtime)

    monitored = {t.asin for t in tasks}
    running = sum(1 for t in tasks if t.status in (TaskStatus.PENDING, TaskStatus.RUNNING))
    completed = [t for t in tasks if t.status == TaskStatus.COMPLETED]

    cluster_count = sum(t.summary.cluster_count or 0 for t in completed)
    veto_count = sum(1 for t in completed if t.summary.veto_status == "VETOED")
    veto_count += sum(
        1
        for t in completed
        for p in proposals_of(t)
        if p.get("status") == "VETOED"
    )

    savings = 0.0
    for t in completed:
        for p in proposals_of(t):
            if p.get("track_type") == "PACKAGING_FULFILLMENT":
                savings += p.get("fulfillment_saving_usd_per_unit", 0.0) * DEFAULT_MONTHLY_VOLUME

    ratings = [t.summary.avg_rating for t in completed if t.summary.avg_rating is not None]
    neg_rates = [
        t.summary.negative_review_rate
        for t in completed
        if t.summary.negative_review_rate is not None
    ]

    data = DashboardOverview(
        monitored_product_count=len(monitored),
        running_task_count=running,
        pain_point_cluster_count=cluster_count,
        fba_saving_pool_usd=round(savings, 2),
        veto_triggered_count=veto_count,
        avg_rating=round(sum(ratings) / len(ratings), 2) if ratings else None,
        negative_review_rate=(
            round(sum(neg_rates) / len(neg_rates), 2) if neg_rates else None
        ),
    )
    return Envelope(data=data)


@router.get("/recommendations", response_model=Envelope[PageData[RecommendationItem]])
async def recommendations(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=3, ge=1, le=20),
    runtime: Runtime = Depends(get_runtime),
) -> Envelope[PageData[RecommendationItem]]:
    tasks = await _scan_tasks(runtime)
    completed = [t for t in tasks if t.status == TaskStatus.COMPLETED]

    items: list[RecommendationItem] = []
    for t in completed:
        passed = [p for p in proposals_of(t) if p.get("status") == "PASSED"]
        if not passed:
            continue
        best = max(passed, key=lambda p: p.get("estimated_roi") or 0)
        items.append(
            RecommendationItem(
                task_id=t.task_id,
                product_id=t.product_id,
                asin=t.asin,
                title=best.get("title"),
                main_image_url=None,
                estimated_roi=best.get("estimated_roi"),
                return_rate_reduction=best.get("defect_rate_reduction"),
                veto_status=t.summary.veto_status,
                finished_at=t.finished_at,
            )
        )
    items.sort(key=lambda i: i.estimated_roi or 0, reverse=True)
    total = len(items)
    start = (page - 1) * page_size
    return Envelope(
        data=PageData[RecommendationItem](
            items=items[start : start + page_size], total=total, page=page, page_size=page_size
        )
    )
