"""Competitor radar endpoints: BSR trends and cross-platform SKU matrix."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from insightx.database import get_session
from insightx.dependencies import get_tenant_id
from insightx.schemas import (
    BsrTrendsResponse,
    CrossPlatformResponse,
    SuccessEnvelope,
)
from insightx.services import radar as radar_svc

router = APIRouter(prefix="/radar", tags=["radar"])


@router.get("/bsr-trends")
def get_bsr_trends(
    task_id: str | None = Query(None, description="Optional task ID to filter ASINs"),
    asin: str | None = Query(None, description="Optional target ASIN"),
    days: int = Query(30, ge=7, le=90, description="Time series window in days"),
    tenant_id: str = Depends(get_tenant_id),
    session: Session = Depends(get_session),  # noqa: B008
) -> SuccessEnvelope[BsrTrendsResponse]:
    """Retrieve BSR and price time series trends for monitored competitor ASINs."""
    data = radar_svc.get_bsr_trends(
        session,
        tenant_id=tenant_id,
        task_id=task_id,
        asin=asin,
        days=days,
    )
    return SuccessEnvelope(data=data)


@router.get("/cross-platform")
def get_cross_platform(
    asin: str | None = Query(None, description="Filter by target Amazon ASIN"),
    platform: str | None = Query(None, description="Filter by platform (TIKTOK, TEMU, ALL)"),
    status: str | None = Query(None, description="Filter by status (MATCHED, PENDING, VARIANT, ALL)"),
    tenant_id: str = Depends(get_tenant_id),
    session: Session = Depends(get_session),  # noqa: B008
) -> SuccessEnvelope[CrossPlatformResponse]:
    """Retrieve cross-platform SKU mapping, match scores, and price/fee arbitrage matrix."""
    data = radar_svc.get_cross_platform(
        session,
        tenant_id=tenant_id,
        asin=asin,
        platform=platform,
        status=status,
    )
    return SuccessEnvelope(data=data)
