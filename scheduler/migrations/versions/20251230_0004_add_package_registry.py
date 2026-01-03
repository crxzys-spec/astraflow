"""Add package registry metadata table."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20251230_0004"
down_revision = "20251230_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "package_registry",
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column(
            "source",
            sa.String(length=32),
            nullable=False,
            server_default="published",
        ),
        sa.Column("owner_id", sa.String(length=128), nullable=False),
        sa.Column(
            "visibility",
            sa.String(length=32),
            nullable=False,
            server_default="internal",
        ),
        sa.Column(
            "state",
            sa.String(length=16),
            nullable=False,
            server_default="active",
        ),
        sa.Column("created_by", sa.String(length=128), nullable=True),
        sa.Column("updated_by", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("name", "source"),
    )
    op.create_index("ix_package_registry_owner", "package_registry", ["owner_id"])
    op.create_index(
        "ix_package_registry_visibility",
        "package_registry",
        ["visibility"],
    )
    op.create_index("ix_package_registry_source", "package_registry", ["source"])


def downgrade() -> None:
    op.drop_index("ix_package_registry_source", table_name="package_registry")
    op.drop_index("ix_package_registry_visibility", table_name="package_registry")
    op.drop_index("ix_package_registry_owner", table_name="package_registry")
    op.drop_table("package_registry")
