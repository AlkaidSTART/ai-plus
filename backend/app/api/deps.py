"""请求依赖：P0 预置单企业身份（真实鉴权接入后替换为会话解析）。"""

from fastapi import Request

from app.config import settings


async def current_tenant_id(request: Request) -> str:
    """P0：返回预置租户；所有资源查询必须携带该值做越权隔离（越权按 404）。"""
    return request.headers.get("x-tenant-id", "tenant_preset")


async def preset_project_id() -> str:
    return settings.preset_project_id
