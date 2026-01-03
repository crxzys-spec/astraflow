"""Repository for user and role records."""

from __future__ import annotations

from typing import Iterable, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from scheduler_api.db.models import RoleRecord, UserRecord, UserRoleRecord
from scheduler_api.db.session import run_in_session_async


class UserRepository:
    def list_users(self, *, session: Session) -> list[UserRecord]:
        stmt = select(UserRecord).order_by(UserRecord.username)
        return list(session.execute(stmt).scalars().all())

    def get(self, user_id: str, *, session: Session) -> Optional[UserRecord]:
        return session.get(UserRecord, user_id)

    def get_by_username(
        self,
        username: str,
        *,
        session: Session,
    ) -> Optional[UserRecord]:
        stmt = select(UserRecord).where(UserRecord.username == username)
        return session.execute(stmt).scalar_one_or_none()

    def save(
        self,
        record: UserRecord,
        *,
        session: Session,
    ) -> UserRecord:
        session.add(record)
        return record

    def list_role_names(
        self,
        user_id: str,
        *,
        session: Session,
    ) -> list[str]:
        stmt = (
            select(RoleRecord.name)
            .join(UserRoleRecord, UserRoleRecord.role_id == RoleRecord.id)
            .where(UserRoleRecord.user_id == user_id)
            .order_by(RoleRecord.name)
        )
        return list(session.execute(stmt).scalars().all())

    async def get_async(
        self,
        user_id: str,
        *,
        session: AsyncSession,
    ) -> Optional[UserRecord]:
        return await session.get(UserRecord, user_id)

    async def list_role_names_async(
        self,
        user_id: str,
        *,
        session: AsyncSession,
    ) -> list[str]:
        stmt = (
            select(RoleRecord.name)
            .join(UserRoleRecord, UserRoleRecord.role_id == RoleRecord.id)
            .where(UserRoleRecord.user_id == user_id)
            .order_by(RoleRecord.name)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    def get_user_role(
        self,
        *,
        user_id: str,
        role_id: str,
        session: Session,
    ) -> Optional[UserRoleRecord]:
        stmt = select(UserRoleRecord).where(
            UserRoleRecord.user_id == user_id,
            UserRoleRecord.role_id == role_id,
        )
        return session.execute(stmt).scalar_one_or_none()

    def add_role(
        self,
        *,
        user_id: str,
        role_id: str,
        session: Session,
    ) -> UserRoleRecord:
        record = UserRoleRecord(user_id=user_id, role_id=role_id)
        session.add(record)
        return record

    def remove_role(
        self,
        *,
        record: UserRoleRecord,
        session: Session,
    ) -> None:
        session.delete(record)

    def get_display_name(
        self,
        user_id: Optional[str],
        *,
        session: Session,
    ) -> Optional[str]:
        if not user_id:
            return None
        record = self.get(user_id, session=session)
        return record.display_name if record else None


class RoleRepository:
    def get_by_name(
        self,
        name: str,
        *,
        session: Session,
    ) -> Optional[RoleRecord]:
        stmt = select(RoleRecord).where(RoleRecord.name == name)
        return session.execute(stmt).scalar_one_or_none()

    def list_by_names(
        self,
        names: Iterable[str],
        *,
        session: Session,
    ) -> list[RoleRecord]:
        name_list = [str(value) for value in names]
        if not name_list:
            return []
        stmt = select(RoleRecord).where(RoleRecord.name.in_(name_list))
        return list(session.execute(stmt).scalars().all())


class AsyncUserRepository:
    def __init__(self, users: Optional[UserRepository] = None) -> None:
        self._users = users or UserRepository()

    async def get_with_roles_by_username(
        self,
        username: str,
    ) -> Optional[tuple[UserRecord, list[str]]]:
        async def _fetch(session: AsyncSession) -> Optional[tuple[UserRecord, list[str]]]:
            result = await session.execute(select(UserRecord).where(UserRecord.username == username))
            user = result.scalar_one_or_none()
            if not user:
                return None
            roles = await self._users.list_role_names_async(user.id, session=session)
            return user, roles

        return await run_in_session_async(_fetch)

    async def get_with_roles_by_id(
        self,
        user_id: str,
    ) -> Optional[tuple[UserRecord, list[str]]]:
        async def _fetch(session: AsyncSession) -> Optional[tuple[UserRecord, list[str]]]:
            user = await self._users.get_async(user_id, session=session)
            if not user:
                return None
            roles = await self._users.list_role_names_async(user.id, session=session)
            return user, roles

        return await run_in_session_async(_fetch)
