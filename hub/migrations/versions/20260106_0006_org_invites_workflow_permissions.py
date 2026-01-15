"""Add org invites, workflow permissions, and org-scoped tokens."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260106_0006"
down_revision = "20260105_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "hub_tokens",
        sa.Column("org_id", sa.String(length=64), nullable=True),
    )
    op.create_index("ix_hub_tokens_org_id", "hub_tokens", ["org_id"])

    op.create_table(
        "hub_org_invites",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("org_id", sa.String(length=64), nullable=False),
        sa.Column("invited_by", sa.String(length=64), nullable=False),
        sa.Column("invitee_id", sa.String(length=64), nullable=True),
        sa.Column("invitee_email", sa.String(length=255), nullable=True),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["org_id"], ["hub_orgs.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_hub_org_invites_org_id", "hub_org_invites", ["org_id"])
    op.create_index("ix_hub_org_invites_invitee_id", "hub_org_invites", ["invitee_id"])

    op.create_table(
        "hub_workflow_permissions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("workflow_id", sa.String(length=64), nullable=False),
        sa.Column("subject_type", sa.String(length=32), nullable=False),
        sa.Column("subject_id", sa.String(length=64), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["workflow_id"],
            ["hub_workflows.id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "workflow_id",
            "subject_type",
            "subject_id",
            name="uq_hub_workflow_permission",
        ),
    )
    op.create_index(
        "ix_hub_workflow_permissions_workflow_id",
        "hub_workflow_permissions",
        ["workflow_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_hub_workflow_permissions_workflow_id",
        table_name="hub_workflow_permissions",
    )
    op.drop_table("hub_workflow_permissions")
    op.drop_index("ix_hub_org_invites_invitee_id", table_name="hub_org_invites")
    op.drop_index("ix_hub_org_invites_org_id", table_name="hub_org_invites")
    op.drop_table("hub_org_invites")
    op.drop_index("ix_hub_tokens_org_id", table_name="hub_tokens")
    op.drop_column("hub_tokens", "org_id")
