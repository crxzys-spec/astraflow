"""Introduce soft-delete support for workflows."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20251118_0008"
down_revision = "20251105_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "workflows",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("workflows", "deleted_at")
