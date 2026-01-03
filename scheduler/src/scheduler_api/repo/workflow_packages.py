"""Repository for workflow packages and versions."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from scheduler_api.db.models import WorkflowPackageRecord, WorkflowPackageVersionRecord


class WorkflowPackageRepository:
    def list(
        self,
        *,
        limit: int,
        owner_filter: Optional[str],
        requester_id: Optional[str],
        visibility: Optional[str],
        search: Optional[str],
        session: Session,
    ) -> list[WorkflowPackageRecord]:
        stmt = select(WorkflowPackageRecord).order_by(WorkflowPackageRecord.updated_at.desc())
        stmt = stmt.limit(limit)
        stmt = stmt.where(WorkflowPackageRecord.deleted_at.is_(None))

        if owner_filter:
            stmt = stmt.where(WorkflowPackageRecord.owner_id == owner_filter)
        else:
            stmt = stmt.where(
                or_(
                    WorkflowPackageRecord.visibility == "public",
                    WorkflowPackageRecord.owner_id == requester_id,
                )
            )

        if visibility:
            stmt = stmt.where(WorkflowPackageRecord.visibility == visibility)

        if search:
            pattern = f"%{search.lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(WorkflowPackageRecord.slug).like(pattern),
                    func.lower(WorkflowPackageRecord.display_name).like(pattern),
                    func.lower(WorkflowPackageRecord.summary).like(pattern),
                )
            )

        return list(session.execute(stmt).scalars().all())

    def get(
        self,
        package_id: str,
        *,
        session: Session,
    ) -> Optional[WorkflowPackageRecord]:
        return session.get(WorkflowPackageRecord, package_id)

    def get_by_slug(
        self,
        slug: str,
        *,
        session: Session,
    ) -> Optional[WorkflowPackageRecord]:
        stmt = select(WorkflowPackageRecord).where(WorkflowPackageRecord.slug == slug)
        return session.execute(stmt).scalar_one_or_none()

    def save(
        self,
        record: WorkflowPackageRecord,
        *,
        session: Session,
    ) -> WorkflowPackageRecord:
        session.add(record)
        return record


class WorkflowPackageVersionRepository:
    def list_by_package(
        self,
        package_id: str,
        *,
        session: Session,
    ) -> list[WorkflowPackageVersionRecord]:
        stmt = (
            select(WorkflowPackageVersionRecord)
            .where(WorkflowPackageVersionRecord.package_id == package_id)
            .order_by(WorkflowPackageVersionRecord.published_at.desc())
        )
        return list(session.execute(stmt).scalars().all())

    def get_latest_versions(
        self,
        package_ids: list[str],
        *,
        session: Session,
    ) -> dict[str, WorkflowPackageVersionRecord]:
        if not package_ids:
            return {}
        stmt = (
            select(WorkflowPackageVersionRecord)
            .where(WorkflowPackageVersionRecord.package_id.in_(package_ids))
            .order_by(
                WorkflowPackageVersionRecord.package_id,
                WorkflowPackageVersionRecord.published_at.desc(),
            )
        )
        rows = session.execute(stmt).scalars().all()
        latest: dict[str, WorkflowPackageVersionRecord] = {}
        for row in rows:
            if row.package_id not in latest:
                latest[row.package_id] = row
        return latest

    def get_by_id(
        self,
        version_id: str,
        *,
        session: Session,
    ) -> Optional[WorkflowPackageVersionRecord]:
        return session.get(WorkflowPackageVersionRecord, version_id)

    def get_by_version(
        self,
        *,
        package_id: str,
        version: str,
        session: Session,
    ) -> Optional[WorkflowPackageVersionRecord]:
        stmt = select(WorkflowPackageVersionRecord).where(
            WorkflowPackageVersionRecord.package_id == package_id,
            WorkflowPackageVersionRecord.version == version,
        )
        return session.execute(stmt).scalar_one_or_none()

    def save(
        self,
        record: WorkflowPackageVersionRecord,
        *,
        session: Session,
    ) -> WorkflowPackageVersionRecord:
        session.add(record)
        return record
