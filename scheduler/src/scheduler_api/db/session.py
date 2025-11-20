"""Database session and engine helpers."""

from __future__ import annotations

import os
from pathlib import Path
from typing import AsyncIterator, Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.engine.url import URL, make_url
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from .base import Base
from . import models  # noqa: F401  # ensure models are imported for metadata

PROJECT_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_DB_PATH = PROJECT_ROOT / "var" / "data" / "scheduler.db"


def _resolve_database_url() -> str:
    raw_url = os.getenv("ASTRAFLOW_DATABASE_URL")
    if not raw_url:
        DEFAULT_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{DEFAULT_DB_PATH.as_posix()}"

    url: URL = make_url(raw_url)
    if url.drivername.startswith("sqlite") and url.database:
        db_path = Path(url.database)
        if not db_path.is_absolute():
            db_path = PROJECT_ROOT / db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        url = url.set(database=str(db_path))
    return str(url)


DATABASE_URL = _resolve_database_url()


def _resolve_async_database_url(sync_url: str) -> str:
    url = make_url(sync_url)
    driver = url.drivername
    driver_map = {
        "sqlite": "sqlite+aiosqlite",
        "sqlite+pysqlite": "sqlite+aiosqlite",
        "postgresql": "postgresql+asyncpg",
        "postgresql+psycopg2": "postgresql+asyncpg",
        "postgres": "postgresql+asyncpg",
        "mysql": "mysql+aiomysql",
        "mysql+pymysql": "mysql+aiomysql",
        "mariadb": "mariadb+aiomysql",
    }
    async_driver = driver_map.get(driver)
    if async_driver is None:
        async_driver = driver if "async" in driver else driver
    return str(url.set(drivername=async_driver))


_SQLITE_CONNECT_ARGS: dict[str, object] = (
    {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)

engine: Engine = create_engine(
    DATABASE_URL,
    echo=False,
    future=True,
    pool_pre_ping=True,
    connect_args=_SQLITE_CONNECT_ARGS,
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    future=True,
    expire_on_commit=False,
)

ASYNC_DATABASE_URL = _resolve_async_database_url(DATABASE_URL)

async_engine: AsyncEngine = create_async_engine(
    ASYNC_DATABASE_URL,
    echo=False,
    future=True,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    expire_on_commit=False,
)


def get_session() -> Iterator[Session]:
    """Provide a transactional scope around a series of operations."""

    session: Session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


async def get_async_session() -> AsyncIterator[AsyncSession]:
    """Provide an async transactional scope around a series of operations."""

    async with AsyncSessionLocal() as session:
        yield session


__all__ = [
    "Base",
    "SessionLocal",
    "AsyncSessionLocal",
    "engine",
    "async_engine",
    "get_session",
    "get_async_session",
    "DATABASE_URL",
    "ASYNC_DATABASE_URL",
]
