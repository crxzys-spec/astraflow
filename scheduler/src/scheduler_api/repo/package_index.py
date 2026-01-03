"""Repository for package index records."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from scheduler_api.db.models import PackageIndexRecord


class PackageIndexRepository:
    def list_by_source(self, *, source: str, session: Session) -> list[PackageIndexRecord]:
        stmt = select(PackageIndexRecord).where(PackageIndexRecord.source == source)
        return list(session.execute(stmt).scalars().all())

    def list_by_name(
        self,
        *,
        name: str,
        source: str,
        session: Session,
    ) -> list[PackageIndexRecord]:
        stmt = select(PackageIndexRecord).where(
            PackageIndexRecord.source == source,
            PackageIndexRecord.name == name,
        )
        return list(session.execute(stmt).scalars().all())

    def list_by_owner(
        self,
        *,
        owner_id: str,
        source: str,
        session: Session,
    ) -> list[PackageIndexRecord]:
        stmt = select(PackageIndexRecord).where(
            PackageIndexRecord.source == source,
            PackageIndexRecord.owner_id == owner_id,
        )
        return list(session.execute(stmt).scalars().all())

    def get_by_name_version(
        self,
        *,
        name: str,
        version: str,
        source: str,
        session: Session,
    ) -> PackageIndexRecord | None:
        stmt = select(PackageIndexRecord).where(
            PackageIndexRecord.source == source,
            PackageIndexRecord.name == name,
            PackageIndexRecord.version == version,
        )
        return session.execute(stmt).scalars().first()
