"""SQLAlchemy models for hub persistence."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, JSON, String, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class HubUser(Base):
    __tablename__ = "hub_users"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    display_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    tokens: Mapped[list["HubToken"]] = relationship(
        "HubToken",
        back_populates="owner",
        cascade="all, delete-orphan",
    )


class HubToken(Base):
    __tablename__ = "hub_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    owner_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("hub_users.id", ondelete="CASCADE"),
        index=True,
    )
    label: Mapped[str] = mapped_column(String(128))
    scopes: Mapped[list[str]] = mapped_column(JSON)
    package_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    token: Mapped[str] = mapped_column(String(128), unique=True, index=True)

    owner: Mapped[HubUser] = relationship("HubUser", back_populates="tokens")


class HubPackage(Base):
    __tablename__ = "hub_packages"

    name: Mapped[str] = mapped_column(String(255), primary_key=True)
    name_normalized: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    readme: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tags: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True)
    dist_tags: Mapped[Optional[dict[str, str]]] = mapped_column(JSON, nullable=True)
    latest_version: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    owner_id: Mapped[str] = mapped_column(String(64), index=True)
    owner_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    visibility: Mapped[str] = mapped_column(String(32), default="public")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    versions: Mapped[list["HubPackageVersion"]] = relationship(
        "HubPackageVersion",
        back_populates="package",
        cascade="all, delete-orphan",
    )


class HubPackageVersion(Base):
    __tablename__ = "hub_package_versions"

    package_name: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("hub_packages.name", ondelete="CASCADE"),
        primary_key=True,
    )
    version: Mapped[str] = mapped_column(String(64), primary_key=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    readme: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tags: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True)
    archive_sha256: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    archive_size_bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    archive_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    owner_id: Mapped[str] = mapped_column(String(64), index=True)
    owner_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    visibility: Mapped[str] = mapped_column(String(32), default="public")
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    package: Mapped[HubPackage] = relationship("HubPackage", back_populates="versions")


class HubWorkflow(Base):
    __tablename__ = "hub_workflows"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tags: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True)
    owner_id: Mapped[str] = mapped_column(String(64), index=True)
    owner_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    visibility: Mapped[str] = mapped_column(String(32), default="public")
    preview_image: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    latest_version: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    versions: Mapped[list["HubWorkflowVersion"]] = relationship(
        "HubWorkflowVersion",
        back_populates="workflow",
        cascade="all, delete-orphan",
    )


class HubWorkflowVersion(Base):
    __tablename__ = "hub_workflow_versions"
    __table_args__ = (UniqueConstraint("workflow_id", "version", name="uq_hub_workflow_version"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    workflow_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("hub_workflows.id", ondelete="CASCADE"),
        index=True,
    )
    version: Mapped[str] = mapped_column(String(64))
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tags: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True)
    preview_image: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    dependencies: Mapped[Optional[list[dict[str, str]]]] = mapped_column(JSON, nullable=True)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    publisher_id: Mapped[str] = mapped_column(String(64))
    definition: Mapped[dict] = mapped_column(JSON)
    changelog: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    workflow: Mapped[HubWorkflow] = relationship("HubWorkflow", back_populates="versions")


class HubOrganization(Base):
    __tablename__ = "hub_orgs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    owner_id: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    members: Mapped[list["HubOrganizationMember"]] = relationship(
        "HubOrganizationMember",
        back_populates="organization",
        cascade="all, delete-orphan",
    )
    teams: Mapped[list["HubTeam"]] = relationship(
        "HubTeam",
        back_populates="organization",
        cascade="all, delete-orphan",
    )


class HubOrganizationMember(Base):
    __tablename__ = "hub_org_members"

    org_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("hub_orgs.id", ondelete="CASCADE"),
        primary_key=True,
    )
    user_id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    role: Mapped[str] = mapped_column(String(32))
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    organization: Mapped[HubOrganization] = relationship(
        "HubOrganization",
        back_populates="members",
    )


class HubTeam(Base):
    __tablename__ = "hub_teams"
    __table_args__ = (UniqueConstraint("org_id", "slug", name="uq_hub_team_slug"),)

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    org_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("hub_orgs.id", ondelete="CASCADE"),
        index=True,
    )
    name: Mapped[str] = mapped_column(String(128))
    slug: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    organization: Mapped[HubOrganization] = relationship(
        "HubOrganization",
        back_populates="teams",
    )
    members: Mapped[list["HubTeamMember"]] = relationship(
        "HubTeamMember",
        back_populates="team",
        cascade="all, delete-orphan",
    )


class HubTeamMember(Base):
    __tablename__ = "hub_team_members"

    team_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("hub_teams.id", ondelete="CASCADE"),
        primary_key=True,
    )
    user_id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    team: Mapped[HubTeam] = relationship("HubTeam", back_populates="members")


class HubPackagePermission(Base):
    __tablename__ = "hub_package_permissions"
    __table_args__ = (
        UniqueConstraint(
            "package_name",
            "subject_type",
            "subject_id",
            name="uq_hub_package_permission",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    package_name: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("hub_packages.name", ondelete="CASCADE"),
        index=True,
    )
    subject_type: Mapped[str] = mapped_column(String(32))
    subject_id: Mapped[str] = mapped_column(String(64))
    role: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class HubAuditEvent(Base):
    __tablename__ = "hub_audit_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    action: Mapped[str] = mapped_column(String(128))
    actor_id: Mapped[str] = mapped_column(String(64), index=True)
    target_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    target_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    metadata_json: Mapped[Optional[dict[str, object]]] = mapped_column(
        "metadata", JSON, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
