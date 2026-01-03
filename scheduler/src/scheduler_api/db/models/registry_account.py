"""ORM model for linked registry accounts."""

from __future__ import annotations

from datetime import datetime, timezone

from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> str:
    return str(uuid4())


class RegistryAccountRecord(Base):
    __tablename__ = "registry_accounts"
    __table_args__ = (
        UniqueConstraint("user_id", name="uix_registry_accounts_user"),
        Index("ix_registry_accounts_registry_user_id", "registry_user_id"),
    )

    id: Mapped[str] = mapped_column(String(128), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    registry_user_id: Mapped[str] = mapped_column(String(128), nullable=False)
    registry_username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        onupdate=_utcnow,
        nullable=False,
    )
