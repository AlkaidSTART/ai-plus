"""Root API router. The `/api/v1` prefix is added exactly once in main.py."""

from fastapi import APIRouter

from api.routes import dashboard, financial, health, insight, products, proposals

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(insight.router)
api_router.include_router(dashboard.router)
api_router.include_router(products.router)
api_router.include_router(proposals.router)
api_router.include_router(financial.router)
