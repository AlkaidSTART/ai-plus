"""Financial routes (docs/api.md §9)."""

from fastapi import APIRouter, Depends

from api.errors import ApiError, ErrorCode
from api.schemas.common import Envelope
from api.schemas.financial import FinancialResultOut, SimulateRequest
from api.routes.insight import get_runtime
from services.financial import FinancialEngine
from services.task_results import financial_of

router = APIRouter(tags=["financial"])

engine = FinancialEngine()


@router.post("/financial/simulate")
async def simulate(payload: SimulateRequest) -> Envelope[dict]:
    """无副作用沙盒模拟：不触发 LangGraph、不落库。"""
    return Envelope(data=engine.simulate(payload.model_dump()))


@router.get("/insight/tasks/{task_id}/financial")
async def task_financial(task_id: str, runtime=Depends(get_runtime)) -> Envelope[dict]:
    from api.routes.insight import _get_task_or_404

    task = await _get_task_or_404(runtime, task_id)
    result = financial_of(task)
    if result is None:
        raise ApiError(ErrorCode.NOT_FOUND, f"任务尚无财务决议结果: {task_id}")
    return Envelope(data=result)
