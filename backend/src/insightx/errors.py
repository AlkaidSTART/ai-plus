"""Stable API errors and exception handlers."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class ApiError(Exception):
    """An expected business error that is safe to expose to API clients."""

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        *,
        details: Any = None,
        retryable: bool = False,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details
        self.retryable = retryable


def request_id_from(request: Request) -> str:
    """Return the request ID assigned by the application middleware."""

    request_id = getattr(request.state, "request_id", None)
    return request_id if isinstance(request_id, str) else "req_unknown"


def error_payload(error: ApiError, request: Request) -> dict[str, Any]:
    """Build the documented error envelope."""

    return {
        "error": {
            "code": error.code,
            "message": error.message,
            "details": error.details,
            "retryable": error.retryable,
            "request_id": request_id_from(request),
        }
    }


async def api_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Convert an ``ApiError`` into the stable JSON error envelope."""

    if not isinstance(exc, ApiError):
        raise exc
    return JSONResponse(
        status_code=exc.status_code,
        content=error_payload(exc, request),
    )


def _validation_details(exc: RequestValidationError) -> list[dict[str, Any]]:
    details: list[dict[str, Any]] = []
    for item in exc.errors():
        details.append(
            {
                "loc": [str(part) for part in item.get("loc", ())],
                "message": str(item.get("msg", "Invalid value")),
                "type": str(item.get("type", "value_error")),
            }
        )
    return details


async def validation_error_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """Convert FastAPI request validation failures to ``VALIDATION_ERROR``."""

    if not isinstance(exc, RequestValidationError):
        raise exc
    error = ApiError(
        422,
        "VALIDATION_ERROR",
        "Request validation failed.",
        details=_validation_details(exc),
    )
    return JSONResponse(status_code=422, content=error_payload(error, request))


def install_exception_handlers(app: FastAPI) -> None:
    """Register the handlers shared by every business route."""

    app.add_exception_handler(ApiError, api_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
