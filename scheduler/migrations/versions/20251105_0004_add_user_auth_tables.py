"""Add user authentication tables and workflow audit columns."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from uuid import uuid4

import bcrypt
from alembic import op
import sqlalchemy as sa


revision = "20251105_0004"
down_revision = "20251105_0003"
branch_labels = None
depends_on = None


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=128), primary_key=True),
        sa.Column("username", sa.String(length=255), nullable=False, unique=True),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_table(
        "roles",
        sa.Column("id", sa.String(length=128), primary_key=True),
        sa.Column("name", sa.String(length=128), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=True),
    )
    op.create_table(
        "user_roles",
        sa.Column("id", sa.String(length=128), primary_key=True),
        sa.Column("user_id", sa.String(length=128), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role_id", sa.String(length=128), sa.ForeignKey("roles.id", ondelete="CASCADE"), nullable=False),
        sa.UniqueConstraint("user_id", "role_id", name="uix_user_role"),
    )

    op.add_column("workflows", sa.Column("created_by", sa.String(length=128), nullable=True))
    op.add_column("workflows", sa.Column("updated_by", sa.String(length=128), nullable=True))

    bind = op.get_bind()
    role_rows = [
        ("admin", "Platform administrator"),
        ("workflow.editor", "Create and update workflows"),
        ("workflow.viewer", "View workflows"),
        ("run.viewer", "View runs"),
    ]
    role_ids = {}
    for name, desc in role_rows:
        role_id = str(uuid4())
        role_ids[name] = role_id
        bind.execute(
            sa.text(
                "INSERT INTO roles (id, name, description) VALUES (:id, :name, :description)"
            ),
            {"id": role_id, "name": name, "description": desc},
        )

    admin_password = os.getenv("SCHEDULER_ADMIN_PASSWORD", "changeme")
    admin_hash = bcrypt.hashpw(admin_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    admin_id = str(uuid4())
    now = _utcnow().isoformat()
    bind.execute(
        sa.text(
            """
            INSERT INTO users (id, username, display_name, password_hash, is_active, created_at, updated_at)
            VALUES (:id, :username, :display_name, :password_hash, 1, :created_at, :updated_at)
            """
        ),
        {
            "id": admin_id,
            "username": "admin",
            "display_name": "Administrator",
            "password_hash": admin_hash,
            "created_at": now,
            "updated_at": now,
        },
    )
    bind.execute(
        sa.text("INSERT INTO user_roles (id, user_id, role_id) VALUES (:id, :user_id, :role_id)"),
        {"id": str(uuid4()), "user_id": admin_id, "role_id": role_ids["admin"]},
    )


def downgrade() -> None:
    op.drop_column("workflows", "updated_by")
    op.drop_column("workflows", "created_by")
    op.drop_table("user_roles")
    op.drop_table("roles")
    op.drop_table("users")
