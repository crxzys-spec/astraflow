"""Add token device fields."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260105_0005"
down_revision = "20260101_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("hub_tokens", sa.Column("created_ip", sa.String(length=64), nullable=True))
    op.add_column("hub_tokens", sa.Column("created_user_agent", sa.String(length=512), nullable=True))
    op.add_column("hub_tokens", sa.Column("last_used_ip", sa.String(length=64), nullable=True))
    op.add_column("hub_tokens", sa.Column("last_used_user_agent", sa.String(length=512), nullable=True))


def downgrade() -> None:
    op.drop_column("hub_tokens", "last_used_user_agent")
    op.drop_column("hub_tokens", "last_used_ip")
    op.drop_column("hub_tokens", "created_user_agent")
    op.drop_column("hub_tokens", "created_ip")
