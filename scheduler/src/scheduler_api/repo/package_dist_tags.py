"""Repository for published package dist-tags."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from scheduler_api.db.models import PackageDistTagRecord


class PackageDistTagRepository:
    def list_by_source(
        self,
        *,
        source: str,
        session: Session,
        owner_id: str | None = None,
    ) -> list[PackageDistTagRecord]:
        stmt = select(PackageDistTagRecord).where(PackageDistTagRecord.source == source)
        if owner_id:
            stmt = stmt.where(PackageDistTagRecord.owner_id == owner_id)
        return list(session.execute(stmt).scalars().all())

    def list_by_name(
        self,
        *,
        name: str,
        source: str,
        session: Session,
        owner_id: str | None = None,
    ) -> list[PackageDistTagRecord]:
        stmt = select(PackageDistTagRecord).where(
            PackageDistTagRecord.source == source,
            PackageDistTagRecord.name == name,
        )
        if owner_id:
            stmt = stmt.where(PackageDistTagRecord.owner_id == owner_id)
        return list(session.execute(stmt).scalars().all())

    def get_by_name_tag(
        self,
        *,
        name: str,
        tag: str,
        source: str,
        session: Session,
        owner_id: str | None = None,
    ) -> PackageDistTagRecord | None:
        stmt = select(PackageDistTagRecord).where(
            PackageDistTagRecord.source == source,
            PackageDistTagRecord.name == name,
            PackageDistTagRecord.tag == tag,
        )
        if owner_id:
            stmt = stmt.where(PackageDistTagRecord.owner_id == owner_id)
        return session.execute(stmt).scalars().first()
