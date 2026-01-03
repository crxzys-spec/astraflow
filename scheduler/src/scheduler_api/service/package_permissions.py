"""Service layer for package permission access."""

from __future__ import annotations

import json
from typing import Iterable, Optional

from scheduler_api.db.session import run_in_session
from scheduler_api.repo.package_permissions import PackagePermissionRepository
from scheduler_api.domain.resources import StoredPackagePermission


class PackagePermissionService:
    def __init__(self, repo: Optional[PackagePermissionRepository] = None) -> None:
        self._repo = repo or PackagePermissionRepository()

    def list(
        self,
        *,
        owner_id: str,
        package_name: Optional[str] = None,
    ) -> list[StoredPackagePermission]:
        def _list(session):
            records = self._repo.list(
                owner_id=owner_id,
                package_name=package_name,
                session=session,
            )
            return [_record_to_permission(record) for record in records]

        return run_in_session(_list)

    def upsert(
        self,
        *,
        owner_id: str,
        package_name: str,
        permission_key: str,
        types: Iterable[str],
        actions: Iterable[str],
        providers: Optional[Iterable[str]] = None,
    ) -> StoredPackagePermission:
        def _upsert(session):
            record = self._repo.upsert(
                owner_id=owner_id,
                package_name=package_name,
                permission_key=permission_key,
                types=types,
                actions=actions,
                providers=providers,
                session=session,
            )
            return _record_to_permission(record)

        return run_in_session(_upsert)

    def delete(self, permission_id: str, *, owner_id: str) -> None:
        def _delete(session) -> None:
            self._repo.delete(permission_id, owner_id=owner_id, session=session)

        run_in_session(_delete)


def _parse_list(value: Optional[str]) -> list[str]:
    if not value:
        return []
    try:
        payload = json.loads(value)
    except json.JSONDecodeError:
        return []
    if isinstance(payload, list):
        return [str(item) for item in payload if item is not None]
    return []


def _record_to_permission(record) -> StoredPackagePermission:
    return StoredPackagePermission(
        permission_id=record.id,
        owner_id=record.owner_id,
        package_name=record.package_name,
        permission_key=record.permission_key,
        types=_parse_list(record.types_json),
        providers=_parse_list(record.providers_json),
        actions=_parse_list(record.actions_json),
        created_at=record.created_at,
    )


__all__ = ["PackagePermissionService"]
