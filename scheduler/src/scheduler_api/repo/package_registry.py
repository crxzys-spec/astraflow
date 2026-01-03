"""Repository for package registry records."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from scheduler_api.db.models import PackageRegistryRecord


class PackageRegistryRepository:
    def get_by_name(
        self,
        *,
        name: str,
        source: str,
        session: Session,
    ) -> PackageRegistryRecord | None:
        stmt = select(PackageRegistryRecord).where(
            PackageRegistryRecord.name == name,
            PackageRegistryRecord.source == source,
        )
        return session.execute(stmt).scalars().first()

    def list_by_source(
        self,
        *,
        source: str,
        session: Session,
    ) -> list[PackageRegistryRecord]:
        stmt = select(PackageRegistryRecord).where(PackageRegistryRecord.source == source)
        return list(session.execute(stmt).scalars().all())

    def list_by_names(
        self,
        *,
        names: list[str],
        source: str,
        session: Session,
    ) -> list[PackageRegistryRecord]:
        if not names:
            return []
        stmt = select(PackageRegistryRecord).where(
            PackageRegistryRecord.source == source,
            PackageRegistryRecord.name.in_(names),
        )
        return list(session.execute(stmt).scalars().all())
