"""Top-level API router."""

from fastapi import APIRouter

from insightx.api.v1.financial import router as financial_router
from insightx.api.v1.health import router as health_router
from insightx.api.v1.radar import router as radar_router
from insightx.api.v1.tasks import router as tasks_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(tasks_router)
api_router.include_router(financial_router)
api_router.include_router(radar_router)
