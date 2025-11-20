"""Add deleted_at column to workflow packages."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20251119_0010"
down_revision = "20251119_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "workflow_packages",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("workflow_packages", "deleted_at")

