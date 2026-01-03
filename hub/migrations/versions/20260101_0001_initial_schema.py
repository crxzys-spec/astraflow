"""Initial hub auth schema."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260101_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "hub_users",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("username", sa.String(length=64), nullable=False, unique=True),
        sa.Column("display_name", sa.String(length=128), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_hub_users_username", "hub_users", ["username"], unique=True)

    op.create_table(
        "hub_tokens",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("owner_id", sa.String(length=64), nullable=False),
        sa.Column("label", sa.String(length=128), nullable=False),
        sa.Column("scopes", sa.JSON(), nullable=False),
        sa.Column("package_name", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("token", sa.String(length=128), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["hub_users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_hub_tokens_owner_id", "hub_tokens", ["owner_id"])
    op.create_index("ix_hub_tokens_token", "hub_tokens", ["token"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_hub_tokens_token", table_name="hub_tokens")
    op.drop_index("ix_hub_tokens_owner_id", table_name="hub_tokens")
    op.drop_table("hub_tokens")
    op.drop_index("ix_hub_users_username", table_name="hub_users")
    op.drop_table("hub_users")
