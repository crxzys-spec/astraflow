"""ORM model for package vault entries."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> str:
    return str(uuid4())


class PackageVaultRecord(Base):
    __tablename__ = "package_vault"
    __table_args__ = (
        Index("ix_package_vault_owner_pkg_key", "owner_id", "package_name", "key", unique=True),
    )

    id: Mapped[str] = mapped_column(String(128), primary_key=True, default=_uuid)
    owner_id: Mapped[str] = mapped_column(String(128), nullable=False)
    package_name: Mapped[str] = mapped_column(String(128), nullable=False)
    key: Mapped[str] = mapped_column(String(128), nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
