from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select

from scheduler_api.apis.users_api_base import BaseUsersApi
from scheduler_api.audit import record_audit_event
from scheduler_api.auth.context import get_current_token
from scheduler_api.auth.roles import require_roles
from scheduler_api.auth.service import hash_password
from scheduler_api.db.models import RoleRecord, UserRecord, UserRoleRecord
from scheduler_api.db.session import SessionLocal
from scheduler_api.models.create_user_request import CreateUserRequest
from scheduler_api.models.reset_user_password_request import ResetUserPasswordRequest
from scheduler_api.models.update_user_profile_request import UpdateUserProfileRequest
from scheduler_api.models.update_user_status_request import UpdateUserStatusRequest
from scheduler_api.models.user_list import UserList
from scheduler_api.models.user_role_request import UserRoleRequest
from scheduler_api.models.user_summary import UserSummary


ADMIN_ROLE = ("admin",)


def _require_authenticated() -> str:
    token = get_current_token()
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "forbidden", "message": "Authentication required."},
        )
    return token.sub


def _build_user_summary(session, user: UserRecord) -> UserSummary:
    role_rows = session.execute(
        select(RoleRecord.name)
        .join(UserRoleRecord, UserRoleRecord.role_id == RoleRecord.id)
        .where(UserRoleRecord.user_id == user.id)
        .order_by(RoleRecord.name)
    ).scalars()
    return UserSummary(
        user_id=user.id,
        username=user.username,
        display_name=user.display_name,
        roles=list(role_rows),
        is_active=user.is_active,
    )


class UsersApiImpl(BaseUsersApi):
    async def list_users(
        self,
    ) -> UserList:
        require_roles(*ADMIN_ROLE)
        with SessionLocal() as session:
            users = session.execute(select(UserRecord).order_by(UserRecord.username)).scalars().all()
            items = [_build_user_summary(session, user) for user in users]
        return UserList(items=items)

    async def create_user(
        self,
        create_user_request: CreateUserRequest,
    ) -> UserSummary:
        token = require_roles(*ADMIN_ROLE)
        if create_user_request is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Request body is required")
        with SessionLocal() as session:
            existing = session.execute(
                select(UserRecord).where(UserRecord.username == create_user_request.username)
            ).scalar_one_or_none()
            if existing:
                raise HTTPException(
                    status.HTTP_409_CONFLICT,
                    detail=f"User '{create_user_request.username}' already exists.",
                )
            user = UserRecord(
                username=create_user_request.username,
                display_name=create_user_request.display_name,
                password_hash=hash_password(create_user_request.password),
            )
            session.add(user)
            requested_roles = list(create_user_request.roles or [])
            if requested_roles:
                roles = session.execute(
                    select(RoleRecord).where(RoleRecord.name.in_(requested_roles))
                ).scalars()
                name_to_role = {role.name: role for role in roles}
                for role_name in requested_roles:
                    role = name_to_role.get(role_name)
                    if role is None:
                        raise HTTPException(
                            status.HTTP_404_NOT_FOUND,
                            detail=f"Role '{role_name}' not found.",
                        )
                    session.add(UserRoleRecord(user_id=user.id, role_id=role.id))
            session.commit()

        record_audit_event(
            actor_id=token.sub if token else None,
            action="user.create",
            target_type="user",
            target_id=user.id,
            metadata={"username": user.username, "roles": requested_roles},
        )

        with SessionLocal() as session:
            refreshed = session.get(UserRecord, user.id)
            if refreshed is None:
                raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"User '{user.id}' not found.")
            return _build_user_summary(session, refreshed)

    async def get_user_profile(
        self,
    ) -> UserSummary:
        user_id = _require_authenticated()
        with SessionLocal() as session:
            user = session.get(UserRecord, user_id)
            if not user:
                raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"User '{user_id}' not found.")
            return _build_user_summary(session, user)

    async def update_user_profile(
        self,
        update_user_profile_request: UpdateUserProfileRequest,
    ) -> UserSummary:
        user_id = _require_authenticated()
        if update_user_profile_request is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Request body is required")
        display_name = update_user_profile_request.display_name
        if not display_name or not str(display_name).strip():
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="displayName is required")
        with SessionLocal() as session:
            user = session.get(UserRecord, user_id)
            if not user:
                raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"User '{user_id}' not found.")
            user.display_name = str(display_name).strip()
            session.commit()
            session.refresh(user)
            return _build_user_summary(session, user)

    async def reset_user_password(
        self,
        userId: str,
        reset_user_password_request: ResetUserPasswordRequest,
    ) -> None:
        token = require_roles(*ADMIN_ROLE)
        if reset_user_password_request is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Request body is required")
        with SessionLocal() as session:
            user = session.get(UserRecord, userId)
            if not user:
                raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"User '{userId}' not found.")
            user.password_hash = hash_password(reset_user_password_request.password)
            session.commit()
        record_audit_event(
            actor_id=token.sub if token else None,
            action="user.password.reset",
            target_type="user",
            target_id=userId,
            metadata={"username": user.username},
        )

    async def add_user_role(
        self,
        userId: str,
        user_role_request: UserRoleRequest,
    ) -> None:
        token = require_roles(*ADMIN_ROLE)
        if user_role_request is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Request body is required")
        with SessionLocal() as session:
            user = session.get(UserRecord, userId)
            if not user:
                raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"User '{userId}' not found.")
            role = session.execute(
                select(RoleRecord).where(RoleRecord.name == user_role_request.role)
            ).scalar_one_or_none()
            if not role:
                raise HTTPException(
                    status.HTTP_404_NOT_FOUND, detail=f"Role '{user_role_request.role}' not found."
                )
            existing = session.execute(
                select(UserRoleRecord).where(
                    UserRoleRecord.user_id == user.id, UserRoleRecord.role_id == role.id
                )
            ).scalar_one_or_none()
            if existing:
                return
            session.add(UserRoleRecord(user_id=user.id, role_id=role.id))
            session.commit()
        record_audit_event(
            actor_id=token.sub if token else None,
            action="user.role.add",
            target_type="user",
            target_id=userId,
            metadata={"role": user_role_request.role},
        )

    async def remove_user_role(
        self,
        userId: str,
        role: str,
    ) -> None:
        token = require_roles(*ADMIN_ROLE)
        with SessionLocal() as session:
            user = session.get(UserRecord, userId)
            if not user:
                raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"User '{userId}' not found.")
            role_record = session.execute(
                select(RoleRecord).where(RoleRecord.name == role)
            ).scalar_one_or_none()
            if not role_record:
                raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"Role '{role}' not found.")
            record = session.execute(
                select(UserRoleRecord).where(
                    UserRoleRecord.user_id == user.id, UserRoleRecord.role_id == role_record.id
                )
            ).scalar_one_or_none()
            if not record:
                return
            session.delete(record)
            session.commit()
        record_audit_event(
            actor_id=token.sub if token else None,
            action="user.role.remove",
            target_type="user",
            target_id=userId,
            metadata={"role": role},
        )

    async def update_user_status(
        self,
        userId: str,
        update_user_status_request: UpdateUserStatusRequest,
    ) -> None:
        token = require_roles(*ADMIN_ROLE)
        if update_user_status_request is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Request body is required")
        with SessionLocal() as session:
            user = session.get(UserRecord, userId)
            if not user:
                raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"User '{userId}' not found.")
            user.is_active = update_user_status_request.is_active
            session.commit()

        record_audit_event(
            actor_id=token.sub if token else None,
            action="user.activate" if update_user_status_request.is_active else "user.deactivate",
            target_type="user",
            target_id=userId,
            metadata={"isActive": update_user_status_request.is_active},
        )
