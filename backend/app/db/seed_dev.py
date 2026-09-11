"""开发环境最小预置数据：确定性 tenant/project UUID，仅本地开发使用，生产禁用。

阶段 03 接入真实租户上下文时复用此处 ID；禁止将示例字符串直接写入 UUID 字段。
"""

import asyncio

from app.config import PROJECT_PRESET_ID, TENANT_PRESET_ID, settings
from app.db.models import Project, Tenant
from app.db.session import SessionFactory


async def seed() -> dict[str, str]:
    if settings.app_env == "prod":
        raise RuntimeError("生产环境禁止执行开发播种")
    async with SessionFactory() as session:
        tenant = await session.get(Tenant, TENANT_PRESET_ID)
        if tenant is None:
            tenant = Tenant(id=TENANT_PRESET_ID, name="dev-tenant")
            session.add(tenant)
        project = await session.get(Project, PROJECT_PRESET_ID)
        if project is None:
            project = Project(
                id=PROJECT_PRESET_ID,
                tenant_id=TENANT_PRESET_ID,
                name="project_home",
                marketplace="US",
            )
            session.add(project)
        await session.commit()
    return {"tenant_id": str(TENANT_PRESET_ID), "project_id": str(PROJECT_PRESET_ID)}


if __name__ == "__main__":
    print(asyncio.run(seed()))
