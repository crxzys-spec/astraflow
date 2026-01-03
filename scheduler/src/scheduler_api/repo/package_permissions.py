"""Repository for package permission records."""

from __future__ import annotations

import json
from typing import Iterable, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from scheduler_api.db.models import PackagePermissionRecord


class PackagePermissionRepository:
    def list(
        self,
        *,
        owner_id: str,
        package_name: Optional[str] = None,
        session: Session,
    ) -> list[PackagePermissionRecord]:
        stmt = select(PackagePermissionRecord).where(PackagePermissionRecord.owner_id == owner_id)
        if package_name:
            stmt = stmt.where(PackagePermissionRecord.package_name == package_name)
        return list(session.execute(stmt).scalars().all())

    def upsert(
        self,
        *,
        owner_id: str,
        package_name: str,
        permission_key: str,
        types: Iterable[str],
        actions: Iterable[str],
        providers: Optional[Iterable[str]] = None,
        session: Session,
    ) -> PackagePermissionRecord:
        record = PackagePermissionRecord(
            owner_id=owner_id,
            package_name=package_name,
            permission_key=permission_key,
            types_json=_serialize_list(types),
            providers_json=_serialize_list(providers) if providers is not None else None,
            actions_json=_serialize_list(actions),
        )
        existing = session.execute(
            select(PackagePermissionRecord).where(
                PackagePermissionRecord.owner_id == owner_id,
                PackagePermissionRecord.package_name == package_name,
                PackagePermissionRecord.permission_key == permission_key,
            )
        ).scalars().first()
        if existing:
            existing.types_json = record.types_json
            existing.providers_json = record.providers_json
            existing.actions_json = record.actions_json
            session.add(existing)
            return existing
        session.add(record)
        return record

    def delete(self, permission_id: str, *, owner_id: str, session: Session) -> None:
        record = session.get(PackagePermissionRecord, permission_id)
        if record is None or record.owner_id != owner_id:
            return
        session.delete(record)


def _serialize_list(values: Optional[Iterable[str]]) -> str:
    return json.dumps([str(value) for value in values or []], ensure_ascii=True)
