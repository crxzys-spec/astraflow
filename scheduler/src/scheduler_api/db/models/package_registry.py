"""ORM model for published package registry entries."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class PackageRegistryRecord(Base):
    """Stores ownership and visibility metadata for published packages."""

    __tablename__ = "package_registry"
    __table_args__ = (
        Index("ix_package_registry_owner", "owner_id"),
        Index("ix_package_registry_visibility", "visibility"),
        Index("ix_package_registry_source", "source"),
    )

    name: Mapped[str] = mapped_column(String(128), primary_key=True)
    source: Mapped[str] = mapped_column(String(32), primary_key=True, default="published")
    owner_id: Mapped[str] = mapped_column(String(128), nullable=False)
    visibility: Mapped[str] = mapped_column(String(32), nullable=False, default="internal")
    state: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    created_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        onupdate=_utcnow,
    )
