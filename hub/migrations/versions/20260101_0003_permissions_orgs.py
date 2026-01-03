"""Persist orgs, teams, and package permissions."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260101_0003"
down_revision = "20260101_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "hub_orgs",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("owner_id", sa.String(length=64), nullable=False),
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
    op.create_index("ix_hub_orgs_slug", "hub_orgs", ["slug"], unique=True)
    op.create_index("ix_hub_orgs_owner_id", "hub_orgs", ["owner_id"])

    op.create_table(
        "hub_org_members",
        sa.Column("org_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column(
            "joined_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["org_id"], ["hub_orgs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("org_id", "user_id"),
    )
    op.create_index("ix_hub_org_members_user_id", "hub_org_members", ["user_id"])

    op.create_table(
        "hub_teams",
        sa.Column("id", sa.String(length=128), primary_key=True),
        sa.Column("org_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["org_id"], ["hub_orgs.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("org_id", "slug", name="uq_hub_team_slug"),
    )
    op.create_index("ix_hub_teams_org_id", "hub_teams", ["org_id"])

    op.create_table(
        "hub_team_members",
        sa.Column("team_id", sa.String(length=128), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column(
            "added_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["team_id"], ["hub_teams.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("team_id", "user_id"),
    )
    op.create_index("ix_hub_team_members_user_id", "hub_team_members", ["user_id"])

    op.create_table(
        "hub_package_permissions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("package_name", sa.String(length=255), nullable=False),
        sa.Column("subject_type", sa.String(length=32), nullable=False),
        sa.Column("subject_id", sa.String(length=64), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["package_name"], ["hub_packages.name"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "package_name",
            "subject_type",
            "subject_id",
            name="uq_hub_package_permission",
        ),
    )
    op.create_index(
        "ix_hub_package_permissions_package_name",
        "hub_package_permissions",
        ["package_name"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_hub_package_permissions_package_name",
        table_name="hub_package_permissions",
    )
    op.drop_table("hub_package_permissions")
    op.drop_index("ix_hub_team_members_user_id", table_name="hub_team_members")
    op.drop_table("hub_team_members")
    op.drop_index("ix_hub_teams_org_id", table_name="hub_teams")
    op.drop_table("hub_teams")
    op.drop_index("ix_hub_org_members_user_id", table_name="hub_org_members")
    op.drop_table("hub_org_members")
    op.drop_index("ix_hub_orgs_owner_id", table_name="hub_orgs")
    op.drop_index("ix_hub_orgs_slug", table_name="hub_orgs")
    op.drop_table("hub_orgs")

