"""ORM model for indexed package manifests."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import BigInteger, DateTime, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class PackageIndexRecord(Base):
    """Stores a normalized package manifest snapshot for quick lookup."""

    __tablename__ = "package_index"
    __table_args__ = (
        Index("ix_package_index_name", "name"),
        Index("ix_package_index_source", "source"),
    )

    name: Mapped[str] = mapped_column(String(128), primary_key=True)
    version: Mapped[str] = mapped_column(String(32), primary_key=True)
    source: Mapped[str] = mapped_column(String(32), primary_key=True, default="local")
    schema_version: Mapped[str] = mapped_column(String(16), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    manifest_json: Mapped[str] = mapped_column(Text, nullable=False)
    manifest_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    archive_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    archive_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    archive_size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    owner_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
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
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
    )
