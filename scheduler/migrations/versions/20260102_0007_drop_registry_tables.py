"""Drop registry tables now replaced by Hub."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260102_0007"
down_revision = "20251230_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("ix_registry_accounts_registry_user_id", table_name="registry_accounts")
    op.drop_table("registry_accounts")

    op.drop_index("ix_package_registry_source", table_name="package_registry")
    op.drop_index("ix_package_registry_visibility", table_name="package_registry")
    op.drop_index("ix_package_registry_owner", table_name="package_registry")
    op.drop_table("package_registry")


def downgrade() -> None:
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
    op.create_index("ix_package_registry_visibility", "package_registry", ["visibility"])
    op.create_index("ix_package_registry_source", "package_registry", ["source"])

    op.create_table(
        "registry_accounts",
        sa.Column("id", sa.String(length=128), primary_key=True),
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("registry_user_id", sa.String(length=128), nullable=False),
        sa.Column("registry_username", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", name="uix_registry_accounts_user"),
    )
    op.create_index(
        "ix_registry_accounts_registry_user_id",
        "registry_accounts",
        ["registry_user_id"],
        unique=False,
    )
