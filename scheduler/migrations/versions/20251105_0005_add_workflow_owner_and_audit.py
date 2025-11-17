"""Add workflow owner column and audit_events table."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20251105_0005"
down_revision = "20251105_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "workflows",
        sa.Column("owner_id", sa.String(length=128), nullable=True),
    )
    op.execute(
        sa.text(
            "UPDATE workflows SET owner_id = COALESCE(created_by, updated_by)"
        )
    )

    op.create_table(
        "audit_events",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("actor_id", sa.String(length=128), nullable=True),
        sa.Column("action", sa.String(length=128), nullable=False),
        sa.Column("target_type", sa.String(length=64), nullable=False),
        sa.Column("target_id", sa.String(length=128), nullable=True),
        sa.Column("metadata", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )


def downgrade() -> None:
    op.drop_table("audit_events")
    op.drop_column("workflows", "owner_id")
