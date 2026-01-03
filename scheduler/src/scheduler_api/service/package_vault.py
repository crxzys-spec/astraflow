"""Service layer for package vault access."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable, Optional

from scheduler_api.db.session import run_in_session
from scheduler_api.repo.package_vault import PackageVaultRepository
from scheduler_api.domain.resources import StoredPackageVaultItem


class PackageVaultService:
    def __init__(self, repo: Optional[PackageVaultRepository] = None) -> None:
        self._repo = repo or PackageVaultRepository()

    def list(self, *, owner_id: str, package_name: str) -> list[StoredPackageVaultItem]:
        def _list(session):
            records = self._repo.list(
                owner_id=owner_id,
                package_name=package_name,
                session=session,
            )
            return [_record_to_item(record) for record in records]

        return run_in_session(_list)

    def upsert_items(
        self,
        *,
        owner_id: str,
        package_name: str,
        items: Iterable[tuple[str, str]],
    ) -> list[StoredPackageVaultItem]:
        now = _utcnow()
        def _upsert(session):
            records = self._repo.upsert_items(
                owner_id=owner_id,
                package_name=package_name,
                items=items,
                now=now,
                session=session,
            )
            return [_record_to_item(record) for record in records]

        return run_in_session(_upsert)

    def delete(self, *, owner_id: str, package_name: str, key: str) -> None:
        def _delete(session) -> None:
            self._repo.delete(
                owner_id=owner_id,
                package_name=package_name,
                key=key,
                session=session,
            )

        run_in_session(_delete)

    def get_value(self, *, owner_id: str, package_name: str, key: str) -> Optional[str]:
        def _get(session):
            return self._repo.get_value(
                owner_id=owner_id,
                package_name=package_name,
                key=key,
                session=session,
            )

        return run_in_session(_get)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _record_to_item(record) -> StoredPackageVaultItem:
    return StoredPackageVaultItem(
        item_id=record.id,
        owner_id=record.owner_id,
        package_name=record.package_name,
        key=record.key,
        value=record.value,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


__all__ = ["PackageVaultService"]
