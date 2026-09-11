"""请求依赖：可信服务端身份（P0 预置），生产默认拒绝预置。"""

import uuid

from fastapi import HTTPException

from app.config import settings


async def get_current_tenant_id() -> uuid.UUID:
    """P0：预置租户来自服务端配置，不信任任何请求头；生产模式直接 401。"""
    if settings.app_env == "prod":
        raise HTTPException(status_code=401, detail="预置身份已禁用")
    return uuid.UUID(settings.preset_tenant_id)
