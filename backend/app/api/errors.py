"""api.md §1 错误信封与 code 枚举。"""

from enum import Enum

from fastapi.responses import JSONResponse


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
    status: int, code: ErrorCode, message: str, request_id: str = "req_todo"
) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={
            "error": {
                "code": code.value,
                "message": message,
                "details": [],
                "retryable": False,
                "request_id": request_id,
            }
        },
    )


def not_implemented() -> JSONResponse:
    return error_response(501, ErrorCode.NOT_IMPLEMENTED, "该接口尚未实现")
