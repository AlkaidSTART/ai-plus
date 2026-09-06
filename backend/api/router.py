"""Root API router. The `/api/v1` prefix is added exactly once in main.py."""

from fastapi import APIRouter

from api.routes import health, insight

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(insight.router)
