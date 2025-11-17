"""Placeholder migration to keep revision history consistent."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa  # noqa: F401  # kept for forward compatibility


revision = "20251105_0002"
down_revision = "20251101_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # This revision intentionally left blank; metadata stays inside workflow definitions.
    pass


def downgrade() -> None:
    # Nothing to undo because upgrade performed no schema change.
    pass
