"""Persist hub packages and workflows."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260101_0002"
down_revision = "20260101_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "hub_packages",
        sa.Column("name", sa.String(length=255), primary_key=True),
        sa.Column("name_normalized", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("readme", sa.Text(), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("dist_tags", sa.JSON(), nullable=True),
        sa.Column("latest_version", sa.String(length=64), nullable=True),
        sa.Column("owner_id", sa.String(length=64), nullable=False),
        sa.Column("owner_name", sa.String(length=128), nullable=True),
        sa.Column("visibility", sa.String(length=32), nullable=False, server_default="public"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_hub_packages_name_normalized",
        "hub_packages",
        ["name_normalized"],
        unique=True,
    )
    op.create_index("ix_hub_packages_owner_id", "hub_packages", ["owner_id"])

    op.create_table(
        "hub_package_versions",
        sa.Column("package_name", sa.String(length=255), nullable=False),
        sa.Column("version", sa.String(length=64), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("readme", sa.Text(), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("archive_sha256", sa.String(length=64), nullable=True),
        sa.Column("archive_size_bytes", sa.Integer(), nullable=True),
        sa.Column("archive_path", sa.String(length=512), nullable=True),
        sa.Column("owner_id", sa.String(length=64), nullable=False),
        sa.Column("owner_name", sa.String(length=128), nullable=True),
        sa.Column("visibility", sa.String(length=32), nullable=False, server_default="public"),
        sa.Column(
            "published_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["package_name"], ["hub_packages.name"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("package_name", "version"),
    )
    op.create_index(
        "ix_hub_package_versions_owner_id",
        "hub_package_versions",
        ["owner_id"],
    )

    op.create_table(
        "hub_workflows",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("owner_id", sa.String(length=64), nullable=False),
        sa.Column("owner_name", sa.String(length=128), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("visibility", sa.String(length=32), nullable=False, server_default="public"),
        sa.Column("preview_image", sa.Text(), nullable=True),
        sa.Column("latest_version", sa.String(length=64), nullable=True),
    )
    op.create_index("ix_hub_workflows_owner_id", "hub_workflows", ["owner_id"])

    op.create_table(
        "hub_workflow_versions",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("workflow_id", sa.String(length=64), nullable=False),
        sa.Column("version", sa.String(length=64), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("preview_image", sa.Text(), nullable=True),
        sa.Column("dependencies", sa.JSON(), nullable=True),
        sa.Column(
            "published_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("publisher_id", sa.String(length=64), nullable=False),
        sa.Column("definition", sa.JSON(), nullable=False),
        sa.Column("changelog", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["workflow_id"], ["hub_workflows.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("workflow_id", "version", name="uq_hub_workflow_version"),
    )
    op.create_index(
        "ix_hub_workflow_versions_workflow_id",
        "hub_workflow_versions",
        ["workflow_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_hub_workflow_versions_workflow_id", table_name="hub_workflow_versions")
    op.drop_table("hub_workflow_versions")
    op.drop_index("ix_hub_workflows_owner_id", table_name="hub_workflows")
    op.drop_table("hub_workflows")
    op.drop_index("ix_hub_package_versions_owner_id", table_name="hub_package_versions")
    op.drop_table("hub_package_versions")
    op.drop_index("ix_hub_packages_owner_id", table_name="hub_packages")
    op.drop_index("ix_hub_packages_name_normalized", table_name="hub_packages")
    op.drop_table("hub_packages")

