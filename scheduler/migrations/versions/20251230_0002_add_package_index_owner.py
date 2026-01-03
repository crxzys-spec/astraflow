"""Add owner id to package index."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20251230_0002"
down_revision = "20251230_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("package_index", sa.Column("owner_id", sa.String(length=128), nullable=True))


def downgrade() -> None:
    op.drop_column("package_index", "owner_id")
