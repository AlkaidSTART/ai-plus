"""Error codes and unified error handling (docs/api.md §11)."""

import logging
from enum import IntEnum

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class ErrorCode(IntEnum):
    BAD_REQUEST = 40001
    UNAUTHORIZED = 40101
    NOT_FOUND = 40401
    CONFLICT = 40901
    VALIDATION = 42201
    RATE_LIMITED = 42901
    INTERNAL = 50001
    UPSTREAM = 50201


HTTP_STATUS: dict[int, int] = {
    ErrorCode.BAD_REQUEST: status.HTTP_400_BAD_REQUEST,
    ErrorCode.UNAUTHORIZED: status.HTTP_401_UNAUTHORIZED,
    ErrorCode.NOT_FOUND: status.HTTP_404_NOT_FOUND,
    ErrorCode.CONFLICT: status.HTTP_409_CONFLICT,
    ErrorCode.VALIDATION: 422,
    ErrorCode.RATE_LIMITED: status.HTTP_429_TOO_MANY_REQUESTS,
    ErrorCode.INTERNAL: status.HTTP_500_INTERNAL_SERVER_ERROR,
    ErrorCode.UPSTREAM: status.HTTP_502_BAD_GATEWAY,
}


class ApiError(Exception):
    """Business error carrying an InsightX error code; never leaks `detail`."""

    def __init__(self, code: ErrorCode, message: str, data: object = None) -> None:
        super().__init__(message)
        self.code = int(code)
        self.message = message
        self.data = data
        self.http_status = HTTP_STATUS.get(self.code, status.HTTP_500_INTERNAL_SERVER_ERROR)


def error_envelope(code: int, message: str, data: object = None) -> dict:
    return {"code": code, "message": message, "data": data}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.http_status,
            content=error_envelope(exc.code, exc.message, exc.data),
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        errors = exc.errors()
        first = errors[0] if errors else {}
        loc = ".".join(str(p) for p in first.get("loc", []) if p != "body")
        msg = first.get("msg", "validation error")
        message = f"参数校验失败: {loc}: {msg}" if loc else f"参数校验失败: {msg}"
        return JSONResponse(
            status_code=422,
            content=error_envelope(ErrorCode.VALIDATION, message),
        )

    @app.exception_handler(Exception)
    async def _unhandled_handler(request: Request, exc: Exception) -> JSONResponse:
        # Keep diagnostics in logs; never leak internal stack traces to clients.
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_envelope(ErrorCode.INTERNAL, "服务内部错误"),
        )
