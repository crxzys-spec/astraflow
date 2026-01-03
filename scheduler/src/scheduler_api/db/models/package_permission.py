"""ORM model for package permission grants."""

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


class PackagePermissionRecord(Base):
    __tablename__ = "package_permissions"
    __table_args__ = (
        Index("ix_package_permissions_owner_pkg_key", "owner_id", "package_name", "permission_key", unique=True),
    )

    id: Mapped[str] = mapped_column(String(128), primary_key=True, default=_uuid)
    owner_id: Mapped[str] = mapped_column(String(128), nullable=False)
    package_name: Mapped[str] = mapped_column(String(128), nullable=False)
    permission_key: Mapped[str] = mapped_column(String(128), nullable=False)
    types_json: Mapped[str] = mapped_column("types", Text, nullable=False)
    providers_json: Mapped[str | None] = mapped_column("providers", Text, nullable=True)
    actions_json: Mapped[str] = mapped_column("actions", Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
