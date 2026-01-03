"""Service layer for user management."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from scheduler_api.audit import record_audit_event
from scheduler_api.auth.service import hash_password
from scheduler_api.db.models import UserRecord
from scheduler_api.models.create_user_request import CreateUserRequest
from scheduler_api.models.reset_user_password_request import ResetUserPasswordRequest
from scheduler_api.models.update_user_profile_request import UpdateUserProfileRequest
from scheduler_api.models.update_user_status_request import UpdateUserStatusRequest
from scheduler_api.models.user_list import UserList
from scheduler_api.models.user_role_request import UserRoleRequest
from scheduler_api.models.user_summary import UserSummary
from scheduler_api.db.session import run_in_session
from scheduler_api.repo.users import RoleRepository, UserRepository


class UserError(Exception):
    pass


class UserNotFoundError(UserError):
    def __init__(self, user_id: str) -> None:
        super().__init__(f"User '{user_id}' not found.")
        self.user_id = user_id


class UsernameConflictError(UserError):
    def __init__(self, username: str) -> None:
        super().__init__(f"User '{username}' already exists.")
        self.username = username


class RoleNotFoundError(UserError):
    def __init__(self, role: str) -> None:
        super().__init__(f"Role '{role}' not found.")
        self.role = role


class UserValidationError(UserError):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


@dataclass(frozen=True)
class _UserAuditSnapshot:
    user_id: str
    username: str
    roles: list[str]


class UserService:
    def __init__(
        self,
        users: Optional[UserRepository] = None,
        roles: Optional[RoleRepository] = None,
    ) -> None:
        self._users = users or UserRepository()
        self._roles = roles or RoleRepository()

    def list_users(self) -> UserList:
        def _list(session):
            users = self._users.list_users(session=session)
            return [self._build_summary(user, session=session) for user in users]

        summaries = run_in_session(_list)
        return UserList(items=summaries)

    def create_user(
        self,
        request: CreateUserRequest,
        *,
        actor_id: Optional[str],
    ) -> UserSummary:
        if request is None:
            raise UserValidationError("Request body is required")

        def _create(session) -> _UserAuditSnapshot:
            existing = self._users.get_by_username(request.username, session=session)
            if existing:
                raise UsernameConflictError(request.username)
            user = UserRecord(
                username=request.username,
                display_name=request.display_name,
                password_hash=hash_password(request.password),
            )
            self._users.save(user, session=session)
            requested_roles = list(request.roles or [])
            if requested_roles:
                role_rows = self._roles.list_by_names(requested_roles, session=session)
                name_to_role = {role.name: role for role in role_rows}
                for role_name in requested_roles:
                    role = name_to_role.get(role_name)
                    if role is None:
                        raise RoleNotFoundError(role_name)
                    existing_role = self._users.get_user_role(
                        user_id=user.id,
                        role_id=role.id,
                        session=session,
                    )
                    if existing_role:
                        continue
                    self._users.add_role(user_id=user.id, role_id=role.id, session=session)
            return _UserAuditSnapshot(user_id=user.id, username=user.username, roles=requested_roles)

        snapshot = run_in_session(_create)
        record_audit_event(
            actor_id=actor_id,
            action="user.create",
            target_type="user",
            target_id=snapshot.user_id,
            metadata={"username": snapshot.username, "roles": snapshot.roles},
        )
        return self.get_user_summary(snapshot.user_id)

    def get_user_summary(self, user_id: str) -> UserSummary:
        def _get(session):
            user = self._users.get(user_id, session=session)
            if not user:
                raise UserNotFoundError(user_id)
            return self._build_summary(user, session=session)

        return run_in_session(_get)

    def update_user_profile(
        self,
        user_id: str,
        request: UpdateUserProfileRequest,
    ) -> UserSummary:
        if request is None:
            raise UserValidationError("Request body is required")
        display_name = request.display_name
        if not display_name or not str(display_name).strip():
            raise UserValidationError("displayName is required")

        def _update(session) -> None:
            user = self._users.get(user_id, session=session)
            if not user:
                raise UserNotFoundError(user_id)
            user.display_name = str(display_name).strip()

        run_in_session(_update)
        return self.get_user_summary(user_id)

    def reset_user_password(
        self,
        user_id: str,
        request: ResetUserPasswordRequest,
        *,
        actor_id: Optional[str],
    ) -> None:
        if request is None:
            raise UserValidationError("Request body is required")

        def _reset(session) -> str:
            user = self._users.get(user_id, session=session)
            if not user:
                raise UserNotFoundError(user_id)
            user.password_hash = hash_password(request.password)
            return user.username

        username = run_in_session(_reset)
        record_audit_event(
            actor_id=actor_id,
            action="user.password.reset",
            target_type="user",
            target_id=user_id,
            metadata={"username": username},
        )

    def add_user_role(
        self,
        user_id: str,
        request: UserRoleRequest,
        *,
        actor_id: Optional[str],
    ) -> None:
        if request is None:
            raise UserValidationError("Request body is required")

        def _add(session) -> bool:
            user = self._users.get(user_id, session=session)
            if not user:
                raise UserNotFoundError(user_id)
            role = self._roles.get_by_name(request.role, session=session)
            if not role:
                raise RoleNotFoundError(request.role)
            existing = self._users.get_user_role(
                user_id=user.id,
                role_id=role.id,
                session=session,
            )
            if existing:
                return False
            self._users.add_role(user_id=user.id, role_id=role.id, session=session)
            return True

        added = run_in_session(_add)
        if added:
            record_audit_event(
                actor_id=actor_id,
                action="user.role.add",
                target_type="user",
                target_id=user_id,
                metadata={"role": request.role},
            )

    def remove_user_role(
        self,
        user_id: str,
        role_name: str,
        *,
        actor_id: Optional[str],
    ) -> None:
        def _remove(session) -> bool:
            user = self._users.get(user_id, session=session)
            if not user:
                raise UserNotFoundError(user_id)
            role = self._roles.get_by_name(role_name, session=session)
            if not role:
                raise RoleNotFoundError(role_name)
            record = self._users.get_user_role(
                user_id=user.id,
                role_id=role.id,
                session=session,
            )
            if not record:
                return False
            self._users.remove_role(record=record, session=session)
            return True

        removed = run_in_session(_remove)
        if removed:
            record_audit_event(
                actor_id=actor_id,
                action="user.role.remove",
                target_type="user",
                target_id=user_id,
                metadata={"role": role_name},
            )

    def update_user_status(
        self,
        user_id: str,
        request: UpdateUserStatusRequest,
        *,
        actor_id: Optional[str],
    ) -> None:
        if request is None:
            raise UserValidationError("Request body is required")

        def _update(session) -> None:
            user = self._users.get(user_id, session=session)
            if not user:
                raise UserNotFoundError(user_id)
            user.is_active = request.is_active

        run_in_session(_update)
        record_audit_event(
            actor_id=actor_id,
            action="user.activate" if request.is_active else "user.deactivate",
            target_type="user",
            target_id=user_id,
            metadata={"isActive": request.is_active},
        )

    def _build_summary(self, user: UserRecord, *, session) -> UserSummary:
        roles = self._users.list_role_names(user.id, session=session)
        return UserSummary(
            user_id=user.id,
            username=user.username,
            display_name=user.display_name,
            roles=roles,
            is_active=user.is_active,
        )


__all__ = [
    "UserService",
    "UserError",
    "UserNotFoundError",
    "UsernameConflictError",
    "RoleNotFoundError",
    "UserValidationError",
]
