"""请求级 ID：中间件写入 ContextVar，错误信封自动携带。"""

import uuid
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware

request_id_ctx: ContextVar[str] = ContextVar("request_id", default="req_todo")


def new_request_id() -> str:
    return "req_" + uuid.uuid4().hex[:16]


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        request_id_ctx.set(request.headers.get("X-Request-ID") or new_request_id())
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id_ctx.get()
        return response
