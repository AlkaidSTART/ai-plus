"""FastAPI dependencies for tenant identity and pagination."""

from __future__ import annotations

from typing import Annotated

from fastapi import Header, Query, Request

from insightx.config import Settings
from insightx.errors import ApiError


def get_settings(request: Request) -> Settings:
    """Return settings bound to the current application instance."""

    settings = request.app.state.settings
    if not isinstance(settings, Settings):
        raise RuntimeError("Application settings are not configured.")
    return settings


def get_tenant_id(request: Request) -> str:
    """Resolve the server-side tenant or fail closed in required mode."""

    settings = get_settings(request)
    if settings.auth_mode == "required":
        raise ApiError(401, "UNAUTHORIZED", "Authentication is required.")
    return settings.dev_tenant_id


IdempotencyKey = Annotated[
    str,
    Header(alias="Idempotency-Key", min_length=1, max_length=256),
]


LimitQuery = Annotated[int, Query(ge=1, le=100)]
