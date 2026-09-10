"""FastAPI 应用工厂。/health 是唯一真实可用端点，其余 P0 路由为 501 占位。"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import events, reports, tasks
from app.config import settings


def create_app() -> FastAPI:
    app = FastAPI(title="InsightX Backend", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok", "version": "0.1.0", "env": settings.app_env}

    app.include_router(tasks.router, prefix="/api/v1")
    app.include_router(reports.router, prefix="/api/v1")
    app.include_router(events.router, prefix="/api/v1")
    return app


app = create_app()
