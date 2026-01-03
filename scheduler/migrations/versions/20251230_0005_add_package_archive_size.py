"""Add archive size metadata to package index."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20251230_0005"
down_revision = "20251230_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "package_index",
        sa.Column("archive_size_bytes", sa.BigInteger(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("package_index", "archive_size_bytes")
