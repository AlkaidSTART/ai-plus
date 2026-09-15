"""Financial risk control and circuit breaker endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from insightx.database import get_session
from insightx.dependencies import get_tenant_id
from insightx.schemas import (
    FinancialEvaluateRequest,
    FinancialEvaluateResponse,
    FinancialRuleInfo,
    SuccessEnvelope,
)
from insightx.services import financial as financial_svc

router = APIRouter(prefix="/financial", tags=["financial"])


@router.get("/rules")
def get_rules() -> SuccessEnvelope[FinancialRuleInfo]:
    """Return active deterministic financial veto rules and version."""
    rules = financial_svc.get_financial_rules()
    return SuccessEnvelope(data=rules)


@router.post("/evaluate")
def evaluate_financial(
    body: FinancialEvaluateRequest,
    tenant_id: str = Depends(get_tenant_id),
    session: Session = Depends(get_session),  # noqa: B008
) -> SuccessEnvelope[FinancialEvaluateResponse]:
    """Perform deterministic financial risk evaluation and circuit breaker check."""
    result = financial_svc.evaluate_financial_risk(
        body,
        session=session,
        tenant_id=tenant_id,
    )
    return SuccessEnvelope(data=result)
