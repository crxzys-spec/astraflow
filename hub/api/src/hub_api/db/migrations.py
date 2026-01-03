"""Helpers to apply Alembic migrations programmatically for hub."""

from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config

from .session import DATABASE_URL


def upgrade_database() -> None:
    """Run Alembic migrations up to the latest revision."""
    hub_dir = Path(__file__).resolve().parents[4]
    alembic_cfg = Config(str(hub_dir / "alembic.ini"))
    alembic_cfg.attributes["configure_logger"] = False
    alembic_cfg.set_main_option("script_location", str(hub_dir / "migrations"))
    alembic_cfg.set_main_option("sqlalchemy.url", DATABASE_URL)
    command.upgrade(alembic_cfg, "head")
