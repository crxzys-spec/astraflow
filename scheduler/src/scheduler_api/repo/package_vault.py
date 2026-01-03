"""Repository for package vault records."""

from __future__ import annotations

from typing import Iterable, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from scheduler_api.db.models import PackageVaultRecord


class PackageVaultRepository:
    def list(
        self,
        *,
        owner_id: str,
        package_name: str,
        session: Session,
    ) -> list[PackageVaultRecord]:
        stmt = select(PackageVaultRecord).where(
            PackageVaultRecord.owner_id == owner_id,
            PackageVaultRecord.package_name == package_name,
        )
        return list(session.execute(stmt).scalars().all())

    def upsert_items(
        self,
        *,
        owner_id: str,
        package_name: str,
        items: Iterable[tuple[str, str]],
        now,
        session: Session,
    ) -> list[PackageVaultRecord]:
        for key, value in items:
            existing = session.execute(
                select(PackageVaultRecord).where(
                    PackageVaultRecord.owner_id == owner_id,
                    PackageVaultRecord.package_name == package_name,
                    PackageVaultRecord.key == key,
                )
            ).scalars().first()
            if existing:
                existing.value = value
                existing.updated_at = now
                session.add(existing)
            else:
                record = PackageVaultRecord(
                    owner_id=owner_id,
                    package_name=package_name,
                    key=key,
                    value=value,
                    created_at=now,
                    updated_at=now,
                )
                session.add(record)
        return self.list(owner_id=owner_id, package_name=package_name, session=session)

    def delete(self, *, owner_id: str, package_name: str, key: str, session: Session) -> None:
        record = session.execute(
            select(PackageVaultRecord).where(
                PackageVaultRecord.owner_id == owner_id,
                PackageVaultRecord.package_name == package_name,
                PackageVaultRecord.key == key,
            )
        ).scalars().first()
        if record is None:
            return
        session.delete(record)

    def get_value(
        self,
        *,
        owner_id: str,
        package_name: str,
        key: str,
        session: Session,
    ) -> Optional[str]:
        record = session.execute(
            select(PackageVaultRecord).where(
                PackageVaultRecord.owner_id == owner_id,
                PackageVaultRecord.package_name == package_name,
                PackageVaultRecord.key == key,
            )
        ).scalars().first()
        if record is None:
            return None
        return record.value
