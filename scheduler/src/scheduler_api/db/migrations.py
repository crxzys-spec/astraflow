"""Helpers to apply Alembic migrations programmatically."""

from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config

from .session import DATABASE_URL


def upgrade_database() -> None:
    """Run Alembic migrations up to the latest revision."""

    scheduler_dir = Path(__file__).resolve().parents[3]
    alembic_cfg = Config(str(scheduler_dir / "alembic.ini"))
    # Prevent Alembic from overriding the application's logging configuration.
    alembic_cfg.attributes["configure_logger"] = False
    alembic_cfg.set_main_option("script_location", str(scheduler_dir / "migrations"))
    alembic_cfg.set_main_option("sqlalchemy.url", DATABASE_URL)
    command.upgrade(alembic_cfg, "head")


__all__ = ["upgrade_database"]
