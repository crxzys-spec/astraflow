"""Add package index table."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20251230_0001"
down_revision = "de8693e59b50"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "package_index",
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("schema_version", sa.String(length=16), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("manifest_json", sa.Text(), nullable=False),
        sa.Column("manifest_hash", sa.String(length=64), nullable=False),
        sa.Column("archive_path", sa.String(length=512), nullable=True),
        sa.Column("archive_sha256", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("name", "version", "source"),
    )
    op.create_index("ix_package_index_name", "package_index", ["name"])
    op.create_index("ix_package_index_source", "package_index", ["source"])


def downgrade() -> None:
    op.drop_index("ix_package_index_source", table_name="package_index")
    op.drop_index("ix_package_index_name", table_name="package_index")
    op.drop_table("package_index")
