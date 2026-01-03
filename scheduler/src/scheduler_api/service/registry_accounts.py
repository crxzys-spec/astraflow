"""Service layer for linked registry accounts."""

from __future__ import annotations

from dataclasses import dataclass

from scheduler_api.db.models import RegistryAccountRecord
from scheduler_api.db.session import run_in_session
from scheduler_api.repo.registry_accounts import RegistryAccountRepository


@dataclass(frozen=True)
class RegistryAccountSnapshot:
    user_id: str
    registry_user_id: str
    registry_username: str | None

    def to_dict(self) -> dict[str, object]:
        return {
            "userId": self.user_id,
            "registryUserId": self.registry_user_id,
            "registryUsername": self.registry_username,
        }


class RegistryAccountService:
    def __init__(self, repo: RegistryAccountRepository | None = None) -> None:
        self._repo = repo or RegistryAccountRepository()

    def get_by_user_id(self, user_id: str) -> RegistryAccountSnapshot | None:
        def _get(session):
            record = self._repo.get_by_user_id(user_id=user_id, session=session)
            return _to_snapshot(record) if record else None

        return run_in_session(_get)

    def upsert(
        self,
        *,
        user_id: str,
        registry_user_id: str,
        registry_username: str | None,
    ) -> RegistryAccountSnapshot:
        def _upsert(session):
            record = self._repo.get_by_user_id(user_id=user_id, session=session)
            if record is None:
                record = RegistryAccountRecord(
                    user_id=user_id,
                    registry_user_id=registry_user_id,
                    registry_username=registry_username,
                )
            else:
                record.registry_user_id = registry_user_id
                record.registry_username = registry_username
            self._repo.save(record, session=session)
            return record

        record = run_in_session(_upsert)
        return _to_snapshot(record)

    def delete(self, user_id: str) -> None:
        def _delete(session):
            record = self._repo.get_by_user_id(user_id=user_id, session=session)
            if record:
                self._repo.delete(record, session=session)

        run_in_session(_delete)


def _to_snapshot(record: RegistryAccountRecord) -> RegistryAccountSnapshot:
    return RegistryAccountSnapshot(
        user_id=record.user_id,
        registry_user_id=record.registry_user_id,
        registry_username=record.registry_username,
    )


registry_account_service = RegistryAccountService()

__all__ = [
    "RegistryAccountSnapshot",
    "RegistryAccountService",
    "registry_account_service",
]
