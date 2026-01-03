"""ORM model for published package dist-tags."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class PackageDistTagRecord(Base):
    """Maps a dist-tag to a specific package version."""

    __tablename__ = "package_dist_tags"
    __table_args__ = (
        Index("ix_package_dist_tags_name", "name"),
        Index("ix_package_dist_tags_source", "source"),
    )

    name: Mapped[str] = mapped_column(String(128), primary_key=True)
    tag: Mapped[str] = mapped_column(String(64), primary_key=True)
    source: Mapped[str] = mapped_column(String(32), primary_key=True, default="published")
    version: Mapped[str] = mapped_column(String(32), nullable=False)
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
