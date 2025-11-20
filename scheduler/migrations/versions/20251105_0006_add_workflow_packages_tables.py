"""Add workflow package tables for published workflows."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20251105_0006"
down_revision = "20251105_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "workflow_packages",
        sa.Column("id", sa.String(length=128), primary_key=True),
        sa.Column("slug", sa.String(length=128), nullable=False, unique=True),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("visibility", sa.String(length=32), nullable=False, server_default="private"),
        sa.Column("tags", sa.Text(), nullable=True),
        sa.Column("owner_id", sa.String(length=128), nullable=True),
        sa.Column("created_by", sa.String(length=128), nullable=True),
        sa.Column("updated_by", sa.String(length=128), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )

    op.create_table(
        "workflow_package_versions",
        sa.Column("id", sa.String(length=128), primary_key=True),
        sa.Column("package_id", sa.String(length=128), nullable=False),
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.Column("changelog", sa.Text(), nullable=True),
        sa.Column("definition_snapshot", sa.Text(), nullable=False),
        sa.Column(
            "published_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("publisher_id", sa.String(length=128), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(
            ["package_id"],
            ["workflow_packages.id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("package_id", "version", name="uq_package_version"),
    )
    op.create_index(
        "ix_workflow_package_versions_package_id",
        "workflow_package_versions",
        ["package_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_workflow_package_versions_package_id", table_name="workflow_package_versions")
    op.drop_table("workflow_package_versions")
    op.drop_table("workflow_packages")
