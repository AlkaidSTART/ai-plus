"""Add worker lease fields to transactional outbox.

Revision ID: 20260915_outbox_lease
Revises: 20260914_task_api_base
Create Date: 2026-09-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260915_outbox_lease"
down_revision: str | Sequence[str] | None = "20260914_task_api_base"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "outbox_messages",
        sa.Column("locked_by", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "outbox_messages",
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("outbox_messages", "locked_at")
    op.drop_column("outbox_messages", "locked_by")
