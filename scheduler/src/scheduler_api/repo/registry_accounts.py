"""Repository for registry account links."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from scheduler_api.db.models import RegistryAccountRecord


class RegistryAccountRepository:
    def get_by_user_id(
        self,
        *,
        user_id: str,
        session: Session,
    ) -> RegistryAccountRecord | None:
        stmt = select(RegistryAccountRecord).where(RegistryAccountRecord.user_id == user_id)
        return session.execute(stmt).scalars().first()

    def save(self, record: RegistryAccountRecord, *, session: Session) -> None:
        session.add(record)

    def delete(self, record: RegistryAccountRecord, *, session: Session) -> None:
        session.delete(record)
