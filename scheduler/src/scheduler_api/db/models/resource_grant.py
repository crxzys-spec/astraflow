"""ORM model for resource grants."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> str:
    return str(uuid4())


class ResourceGrantRecord(Base):
    __tablename__ = "resource_grants"

    id: Mapped[str] = mapped_column(String(128), primary_key=True, default=_uuid)
    resource_id: Mapped[str] = mapped_column(String(128), nullable=False)
    package_name: Mapped[str] = mapped_column(String(128), nullable=False)
    package_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    resource_key: Mapped[str] = mapped_column(String(128), nullable=False)
    scope: Mapped[str] = mapped_column(String(32), nullable=False)
    workflow_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    actions: Mapped[str] = mapped_column(Text, nullable=False)
    created_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    metadata_json: Mapped[str | None] = mapped_column("metadata", Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
