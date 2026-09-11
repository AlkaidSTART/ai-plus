"""api.md §1 错误信封与 code 枚举。"""

from enum import Enum

from fastapi.responses import JSONResponse

from app.api.request_id import request_id_ctx


class ErrorCode(str, Enum):
    INVALID_ASIN = "INVALID_ASIN"
    INVALID_INPUT = "INVALID_INPUT"
    IDEMPOTENCY_CONFLICT = "IDEMPOTENCY_CONFLICT"
    INVALID_EVENT_CURSOR = "INVALID_EVENT_CURSOR"
    ITEM_NOT_RETRYABLE = "ITEM_NOT_RETRYABLE"
    REPORT_NOT_READY = "REPORT_NOT_READY"
    REPORT_NOT_AVAILABLE = "REPORT_NOT_AVAILABLE"
    NOT_FOUND = "NOT_FOUND"
    UNAUTHORIZED = "UNAUTHORIZED"
    RATE_LIMITED = "RATE_LIMITED"
    NOT_IMPLEMENTED = "NOT_IMPLEMENTED"


def error_response(
    status: int,
    code: ErrorCode,
    message: str,
    details: list | None = None,
    request_id: str | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={
            "error": {
                "code": code.value,
                "message": message,
                "details": details if details is not None else [],
                "retryable": False,
                "request_id": request_id or request_id_ctx.get(),
            }
        },
    )


def not_implemented() -> JSONResponse:
    return error_response(501, ErrorCode.NOT_IMPLEMENTED, "该接口尚未实现")
