"""FastAPI 应用工厂。/health 与任务接口真实可用；报告/SSE 仍 501 占位。"""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.errors import ErrorCode, error_response
from app.api.request_id import RequestIdMiddleware
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
    app.add_middleware(RequestIdMiddleware)

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        return error_response(
            422,
            ErrorCode.INVALID_INPUT,
            "请求参数校验失败",
            details=[
                {"field": ".".join(map(str, error["loc"])), "reason": error["msg"]}
                for error in exc.errors()
            ],
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_error_handler(request: Request, exc: StarletteHTTPException):
        if exc.status_code == 401:
            return error_response(401, ErrorCode.UNAUTHORIZED, str(exc.detail))
        if exc.status_code == 404:
            return error_response(404, ErrorCode.NOT_FOUND, str(exc.detail))
        raise exc

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok", "version": "0.1.0", "env": settings.app_env}

    app.include_router(tasks.router, prefix="/api/v1")
    app.include_router(reports.router, prefix="/api/v1")
    app.include_router(events.router, prefix="/api/v1")
    return app


app = create_app()
