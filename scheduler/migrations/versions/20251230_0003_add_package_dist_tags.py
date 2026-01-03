"""Add package dist-tags and status."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20251230_0003"
down_revision = "20251230_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "package_index",
        sa.Column(
            "status",
            sa.String(length=16),
            nullable=False,
            server_default="active",
        ),
    )
    op.create_table(
        "package_dist_tags",
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("tag", sa.String(length=64), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("name", "tag", "source"),
    )
    op.create_index("ix_package_dist_tags_name", "package_dist_tags", ["name"])
    op.create_index("ix_package_dist_tags_source", "package_dist_tags", ["source"])


def downgrade() -> None:
    op.drop_index("ix_package_dist_tags_source", table_name="package_dist_tags")
    op.drop_index("ix_package_dist_tags_name", table_name="package_dist_tags")
    op.drop_table("package_dist_tags")
    op.drop_column("package_index", "status")
