"""Add registry account links."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20251230_0006"
down_revision = "20251230_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
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


def downgrade() -> None:
    op.drop_index("ix_registry_accounts_registry_user_id", table_name="registry_accounts")
    op.drop_table("registry_accounts")
