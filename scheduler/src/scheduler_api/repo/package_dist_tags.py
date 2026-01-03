"""Repository for published package dist-tags."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from scheduler_api.db.models import PackageDistTagRecord


class PackageDistTagRepository:
    def list_by_source(self, *, source: str, session: Session) -> list[PackageDistTagRecord]:
        stmt = select(PackageDistTagRecord).where(PackageDistTagRecord.source == source)
        return list(session.execute(stmt).scalars().all())

    def list_by_name(
        self,
        *,
        name: str,
        source: str,
        session: Session,
    ) -> list[PackageDistTagRecord]:
        stmt = select(PackageDistTagRecord).where(
            PackageDistTagRecord.source == source,
            PackageDistTagRecord.name == name,
        )
        return list(session.execute(stmt).scalars().all())

    def get_by_name_tag(
        self,
        *,
        name: str,
        tag: str,
        source: str,
        session: Session,
    ) -> PackageDistTagRecord | None:
        stmt = select(PackageDistTagRecord).where(
            PackageDistTagRecord.source == source,
            PackageDistTagRecord.name == name,
            PackageDistTagRecord.tag == tag,
        )
        return session.execute(stmt).scalars().first()
