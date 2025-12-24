"""ORM model for stored resources."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import BigInteger, DateTime, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> str:
    return str(uuid4())


class ResourceRecord(Base):
    __tablename__ = "resources"
    __table_args__ = (
        Index("ix_resources_owner_id", "owner_id"),
        Index("ix_resources_sha256", "sha256"),
    )

    resource_id: Mapped[str] = mapped_column(String(128), primary_key=True, default=_uuid)
    provider: Mapped[str] = mapped_column(String(32), nullable=False, default="local")
    resource_type: Mapped[str] = mapped_column("type", String(32), nullable=False, default="file")
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    owner_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    visibility: Mapped[str | None] = mapped_column(String(32), nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sha256: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[str | None] = mapped_column("metadata", Text, nullable=True)
