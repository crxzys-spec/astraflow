"""Persist audit events."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260101_0004"
down_revision = "20260101_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "hub_audit_events",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("action", sa.String(length=128), nullable=False),
        sa.Column("actor_id", sa.String(length=64), nullable=False),
        sa.Column("target_type", sa.String(length=64), nullable=True),
        sa.Column("target_id", sa.String(length=128), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_hub_audit_events_actor_id", "hub_audit_events", ["actor_id"])
    op.create_index("ix_hub_audit_events_action", "hub_audit_events", ["action"])


def downgrade() -> None:
    op.drop_index("ix_hub_audit_events_action", table_name="hub_audit_events")
    op.drop_index("ix_hub_audit_events_actor_id", table_name="hub_audit_events")
    op.drop_table("hub_audit_events")

