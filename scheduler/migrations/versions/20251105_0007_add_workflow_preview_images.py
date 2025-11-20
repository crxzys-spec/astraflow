"""Add preview image fields to workflows and package versions."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20251105_0007"
down_revision = "20251105_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("workflows", sa.Column("preview_image", sa.Text(), nullable=True))
    op.add_column(
        "workflow_package_versions",
        sa.Column("preview_image", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("workflow_package_versions", "preview_image")
    op.drop_column("workflows", "preview_image")
