"""Add owner_name column to workflow packages."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20251119_0009"
down_revision = "20251118_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "workflow_packages",
        sa.Column("owner_name", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("workflow_packages", "owner_name")

