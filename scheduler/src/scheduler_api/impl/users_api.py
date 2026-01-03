from __future__ import annotations

from scheduler_api.http.errors import bad_request, conflict, forbidden, not_found

from scheduler_api.apis.users_api_base import BaseUsersApi
from scheduler_api.auth.context import get_current_token
from scheduler_api.auth.roles import require_roles
from scheduler_api.models.create_user_request import CreateUserRequest
from scheduler_api.models.reset_user_password_request import ResetUserPasswordRequest
from scheduler_api.models.update_user_profile_request import UpdateUserProfileRequest
from scheduler_api.models.update_user_status_request import UpdateUserStatusRequest
from scheduler_api.models.user_list import UserList
from scheduler_api.models.user_role_request import UserRoleRequest
from scheduler_api.models.user_summary import UserSummary
from scheduler_api.service.users import (
    RoleNotFoundError,
    UserNotFoundError,
    UserService,
    UserValidationError,
    UsernameConflictError,
)


ADMIN_ROLE = ("admin",)

_user_service = UserService()


def _require_authenticated() -> str:
    token = get_current_token()
    if token is None:
        raise forbidden("Authentication required.")
    return token.sub


class UsersApiImpl(BaseUsersApi):
    async def list_users(
        self,
    ) -> UserList:
        require_roles(*ADMIN_ROLE)
        return _user_service.list_users()

    async def create_user(
        self,
        create_user_request: CreateUserRequest,
    ) -> UserSummary:
        token = require_roles(*ADMIN_ROLE)
        try:
            return _user_service.create_user(
                create_user_request,
                actor_id=token.sub if token else None,
            )
        except UserValidationError as exc:
            raise bad_request(exc.message, error="invalid_payload") from exc
        except UsernameConflictError as exc:
            raise conflict(str(exc), error="username_conflict") from exc
        except RoleNotFoundError as exc:
            raise not_found(str(exc), error="role_not_found") from exc

    async def get_user_profile(
        self,
    ) -> UserSummary:
        user_id = _require_authenticated()
        try:
            return _user_service.get_user_summary(user_id)
        except UserNotFoundError as exc:
            raise not_found(str(exc), error="user_not_found") from exc

    async def update_user_profile(
        self,
        update_user_profile_request: UpdateUserProfileRequest,
    ) -> UserSummary:
        user_id = _require_authenticated()
        try:
            return _user_service.update_user_profile(user_id, update_user_profile_request)
        except UserValidationError as exc:
            raise bad_request(exc.message, error="invalid_payload") from exc
        except UserNotFoundError as exc:
            raise not_found(str(exc), error="user_not_found") from exc

    async def reset_user_password(
        self,
        userId: str,
        reset_user_password_request: ResetUserPasswordRequest,
    ) -> None:
        token = require_roles(*ADMIN_ROLE)
        try:
            _user_service.reset_user_password(
                userId,
                reset_user_password_request,
                actor_id=token.sub if token else None,
            )
        except UserValidationError as exc:
            raise bad_request(exc.message, error="invalid_payload") from exc
        except UserNotFoundError as exc:
            raise not_found(str(exc), error="user_not_found") from exc

    async def add_user_role(
        self,
        userId: str,
        user_role_request: UserRoleRequest,
    ) -> None:
        token = require_roles(*ADMIN_ROLE)
        try:
            _user_service.add_user_role(
                userId,
                user_role_request,
                actor_id=token.sub if token else None,
            )
        except UserValidationError as exc:
            raise bad_request(exc.message, error="invalid_payload") from exc
        except UserNotFoundError as exc:
            raise not_found(str(exc), error="user_not_found") from exc
        except RoleNotFoundError as exc:
            raise not_found(str(exc), error="role_not_found") from exc

    async def remove_user_role(
        self,
        userId: str,
        role: str,
    ) -> None:
        token = require_roles(*ADMIN_ROLE)
        try:
            _user_service.remove_user_role(
                userId,
                role,
                actor_id=token.sub if token else None,
            )
        except UserNotFoundError as exc:
            raise not_found(str(exc), error="user_not_found") from exc
        except RoleNotFoundError as exc:
            raise not_found(str(exc), error="role_not_found") from exc

    async def update_user_status(
        self,
        userId: str,
        update_user_status_request: UpdateUserStatusRequest,
    ) -> None:
        token = require_roles(*ADMIN_ROLE)
        try:
            _user_service.update_user_status(
                userId,
                update_user_status_request,
                actor_id=token.sub if token else None,
            )
        except UserValidationError as exc:
            raise bad_request(exc.message, error="invalid_payload") from exc
        except UserNotFoundError as exc:
            raise not_found(str(exc), error="user_not_found") from exc
