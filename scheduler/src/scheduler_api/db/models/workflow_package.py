"""ORM models for workflow packages and their published versions."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class WorkflowPackageRecord(Base):
    """Represents a published workflow package that can host multiple versions."""

    __tablename__ = "workflow_packages"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    slug: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    visibility: Mapped[str] = mapped_column(String(32), nullable=False, default="private")
    tags: Mapped[str | None] = mapped_column(Text, nullable=True)
    owner_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    owner_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
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

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"WorkflowPackageRecord(id={self.id!r}, slug={self.slug!r})"


class WorkflowPackageVersionRecord(Base):
    """Represents a published snapshot of a workflow package."""

    __tablename__ = "workflow_package_versions"
    __table_args__ = (
        UniqueConstraint("package_id", "version", name="uq_package_version"),
        Index("ix_workflow_package_versions_package_id", "package_id"),
    )

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    package_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("workflow_packages.id", ondelete="CASCADE"),
        nullable=False,
    )
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    changelog: Mapped[str | None] = mapped_column(Text, nullable=True)
    definition_snapshot: Mapped[str] = mapped_column(Text, nullable=False)
    preview_image: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
    )
    publisher_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
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

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"WorkflowPackageVersionRecord(id={self.id!r}, version={self.version!r})"
