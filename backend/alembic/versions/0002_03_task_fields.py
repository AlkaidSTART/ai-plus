"""阶段 03 任务字段：完成时间、重试父任务、分项错误。

Revision ID: 0002_03_task_fields — 显式 DDL，只追加，不改 0001。
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0002_03_task_fields"
down_revision: str | None = "0001_p0_core"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "tasks",
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "tasks",
        sa.Column("parent_task_id", UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_tasks_parent_task_id", "tasks", "tasks", ["parent_task_id"], ["id"]
    )
    op.add_column("task_items", sa.Column("error", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("task_items", "error")
    op.drop_constraint("fk_tasks_parent_task_id", "tasks", type_="foreignkey")
    op.drop_column("tasks", "parent_task_id")
    op.drop_column("tasks", "completed_at")
