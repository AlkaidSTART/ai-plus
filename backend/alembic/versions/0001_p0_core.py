"""P0 闭环表初始建表。

Revision ID: 0001_p0_core — 以 app.db.models.Base.metadata 为唯一真相源，
upgrade/downgrade 均从 metadata 派生，避免迁移与模型双写漂移。
P1/P2 表在对应阶段新增独立迁移。
"""

from collections.abc import Sequence

from alembic import op

import app.db.models  # noqa: F401
from app.db.base import Base

revision: str = "0001_p0_core"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
