"""Service layer for published package registry metadata."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable, Optional

from scheduler_api.db.models import PackageRegistryRecord
from scheduler_api.db.session import run_in_session
from scheduler_api.repo.package_index import PackageIndexRepository
from scheduler_api.repo.package_registry import PackageRegistryRepository

PACKAGE_VISIBILITY_PRIVATE = "private"
PACKAGE_VISIBILITY_INTERNAL = "internal"
PACKAGE_VISIBILITY_PUBLIC = "public"
PACKAGE_VISIBILITY_VALUES = {
    PACKAGE_VISIBILITY_PRIVATE,
    PACKAGE_VISIBILITY_INTERNAL,
    PACKAGE_VISIBILITY_PUBLIC,
}

PACKAGE_STATE_ACTIVE = "active"
PACKAGE_STATE_RESERVED = "reserved"
PACKAGE_STATE_VALUES = {
    PACKAGE_STATE_ACTIVE,
    PACKAGE_STATE_RESERVED,
}


class PackageRegistryError(Exception):
    """Base error for package registry operations."""


class PackageRegistryNotFoundError(PackageRegistryError):
    """Raised when a package registry entry is missing."""


class PackageRegistryConflictError(PackageRegistryError):
    """Raised when a registry entry already exists or conflicts."""


class PackageRegistryOwnershipError(PackageRegistryError):
    """Raised when a caller lacks ownership of the registry entry."""


class PackageRegistryVisibilityError(PackageRegistryError):
    """Raised when an invalid visibility value is provided."""


@dataclass(frozen=True)
class PackageRegistrySnapshot:
    name: str
    owner_id: str
    visibility: str
    state: str
    created_at: datetime
    updated_at: datetime
    created_by: str | None
    updated_by: str | None

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "ownerId": self.owner_id,
            "visibility": self.visibility,
            "state": self.state,
            "createdAt": self.created_at,
            "updatedAt": self.updated_at,
            "createdBy": self.created_by,
            "updatedBy": self.updated_by,
        }


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class PackageRegistryService:
    def __init__(
        self,
        repo: Optional[PackageRegistryRepository] = None,
        index_repo: Optional[PackageIndexRepository] = None,
        *,
        source: str = "published",
    ) -> None:
        self._repo = repo or PackageRegistryRepository()
        self._index_repo = index_repo or PackageIndexRepository()
        self._source = source

    def get(self, name: str) -> PackageRegistrySnapshot | None:
        def _get(session):
            record = self._repo.get_by_name(name=name, source=self._source, session=session)
            return _record_to_snapshot(record) if record else None

        return run_in_session(_get)

    def list_by_names(self, names: Iterable[str]) -> list[PackageRegistrySnapshot]:
        name_list = [str(name) for name in names if name]
        if not name_list:
            return []

        def _list(session):
            records = self._repo.list_by_names(
                names=name_list,
                source=self._source,
                session=session,
            )
            return [_record_to_snapshot(record) for record in records]

        return run_in_session(_list)

    def reserve(
        self,
        name: str,
        *,
        owner_id: str,
        visibility: str,
        actor_id: str,
    ) -> PackageRegistrySnapshot:
        if visibility not in PACKAGE_VISIBILITY_VALUES:
            raise PackageRegistryVisibilityError("Invalid package visibility.")
        now = _utcnow()

        def _reserve(session):
            existing = self._repo.get_by_name(name=name, source=self._source, session=session)
            if existing:
                if existing.owner_id != owner_id:
                    raise PackageRegistryConflictError(
                        f"Package '{name}' is already owned by another user."
                    )
                return existing

            versions = self._index_repo.list_by_name(
                name=name,
                source=self._source,
                session=session,
            )
            if versions:
                raise PackageRegistryConflictError(
                    f"Package '{name}' already has published versions."
                )

            record = PackageRegistryRecord(
                name=name,
                source=self._source,
                owner_id=owner_id,
                visibility=visibility,
                state=PACKAGE_STATE_RESERVED,
                created_by=actor_id,
                updated_by=actor_id,
                created_at=now,
                updated_at=now,
            )
            session.add(record)
            return record

        record = run_in_session(_reserve)
        return _record_to_snapshot(record)

    def ensure_publish_access(
        self,
        name: str,
        *,
        actor_id: str,
        require_existing: bool,
        default_visibility: str = PACKAGE_VISIBILITY_INTERNAL,
    ) -> PackageRegistrySnapshot:
        if default_visibility not in PACKAGE_VISIBILITY_VALUES:
            raise PackageRegistryVisibilityError("Invalid package visibility.")
        now = _utcnow()

        def _ensure(session):
            record = self._repo.get_by_name(name=name, source=self._source, session=session)
            if record:
                if record.owner_id != actor_id:
                    raise PackageRegistryOwnershipError(
                        "Only the publisher can publish new versions for this package."
                    )
                if record.state == PACKAGE_STATE_RESERVED:
                    if require_existing:
                        versions = self._index_repo.list_by_name(
                            name=name,
                            source=self._source,
                            session=session,
                        )
                        if not versions:
                            raise PackageRegistryNotFoundError(f"Package '{name}' not found.")
                    record.state = PACKAGE_STATE_ACTIVE
                    record.updated_by = actor_id
                    record.updated_at = now
                    session.add(record)
                return record

            versions = self._index_repo.list_by_name(
                name=name,
                source=self._source,
                session=session,
            )
            if require_existing and not versions:
                raise PackageRegistryNotFoundError(f"Package '{name}' not found.")

            owner_id = actor_id
            owners = {item.owner_id for item in versions if item.owner_id}
            if owners:
                if len(owners) > 1:
                    raise PackageRegistryOwnershipError(
                        "Package ownership is inconsistent; contact an administrator."
                    )
                owner_id = next(iter(owners))
                if owner_id != actor_id:
                    raise PackageRegistryOwnershipError(
                        "Only the publisher can publish new versions for this package."
                    )
            else:
                for record in versions:
                    if record.owner_id is None:
                        record.owner_id = actor_id
                        session.add(record)

            record = PackageRegistryRecord(
                name=name,
                source=self._source,
                owner_id=owner_id,
                visibility=default_visibility,
                state=PACKAGE_STATE_ACTIVE,
                created_by=actor_id,
                updated_by=actor_id,
                created_at=now,
                updated_at=now,
            )
            session.add(record)
            return record

        record = run_in_session(_ensure)
        return _record_to_snapshot(record)

    def update_visibility(
        self,
        name: str,
        *,
        visibility: str,
        actor_id: str,
        is_admin: bool,
    ) -> PackageRegistrySnapshot:
        if visibility not in PACKAGE_VISIBILITY_VALUES:
            raise PackageRegistryVisibilityError("Invalid package visibility.")
        now = _utcnow()

        def _update(session):
            record = self._repo.get_by_name(name=name, source=self._source, session=session)
            if record is None:
                raise PackageRegistryNotFoundError(f"Package '{name}' not found.")
            if record.owner_id != actor_id and not is_admin:
                raise PackageRegistryOwnershipError(
                    "Only the package owner can update visibility."
                )
            record.visibility = visibility
            record.updated_by = actor_id
            record.updated_at = now
            session.add(record)
            return record

        record = run_in_session(_update)
        return _record_to_snapshot(record)

    def transfer_owner(
        self,
        name: str,
        *,
        new_owner_id: str,
        actor_id: str,
        is_admin: bool,
    ) -> PackageRegistrySnapshot:
        now = _utcnow()

        def _transfer(session):
            record = self._repo.get_by_name(name=name, source=self._source, session=session)
            if record is None:
                raise PackageRegistryNotFoundError(f"Package '{name}' not found.")
            if record.owner_id != actor_id and not is_admin:
                raise PackageRegistryOwnershipError(
                    "Only the package owner can transfer ownership."
                )
            if record.owner_id == new_owner_id:
                return record
            record.owner_id = new_owner_id
            record.updated_by = actor_id
            record.updated_at = now
            session.add(record)

            versions = self._index_repo.list_by_name(
                name=name,
                source=self._source,
                session=session,
            )
            for version in versions:
                version.owner_id = new_owner_id
                session.add(version)
            return record

        record = run_in_session(_transfer)
        return _record_to_snapshot(record)

    def can_read(self, record: PackageRegistrySnapshot, *, actor_id: str, is_admin: bool) -> bool:
        if is_admin:
            return True
        if record.visibility != PACKAGE_VISIBILITY_PRIVATE:
            return True
        return record.owner_id == actor_id


def _record_to_snapshot(record: PackageRegistryRecord) -> PackageRegistrySnapshot:
    return PackageRegistrySnapshot(
        name=record.name,
        owner_id=record.owner_id,
        visibility=record.visibility,
        state=record.state,
        created_at=record.created_at,
        updated_at=record.updated_at,
        created_by=record.created_by,
        updated_by=record.updated_by,
    )


package_registry_service = PackageRegistryService()

__all__ = [
    "PACKAGE_VISIBILITY_PRIVATE",
    "PACKAGE_VISIBILITY_INTERNAL",
    "PACKAGE_VISIBILITY_PUBLIC",
    "PACKAGE_VISIBILITY_VALUES",
    "PACKAGE_STATE_ACTIVE",
    "PACKAGE_STATE_RESERVED",
    "PACKAGE_STATE_VALUES",
    "PackageRegistryError",
    "PackageRegistryNotFoundError",
    "PackageRegistryConflictError",
    "PackageRegistryOwnershipError",
    "PackageRegistryVisibilityError",
    "PackageRegistrySnapshot",
    "PackageRegistryService",
    "package_registry_service",
]
