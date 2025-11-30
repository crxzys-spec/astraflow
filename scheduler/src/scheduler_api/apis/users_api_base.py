# coding: utf-8

from typing import ClassVar, Dict, List, Tuple  # noqa: F401

from pydantic import StrictStr
from typing import Any
from scheduler_api.models.create_user_request import CreateUserRequest
from scheduler_api.models.reset_user_password_request import ResetUserPasswordRequest
from scheduler_api.models.update_user_status_request import UpdateUserStatusRequest
from scheduler_api.models.user_list import UserList
from scheduler_api.models.user_role_request import UserRoleRequest
from scheduler_api.models.user_summary import UserSummary
from scheduler_api.security_api import get_token_bearerAuth

class BaseUsersApi:
    subclasses: ClassVar[Tuple] = ()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        BaseUsersApi.subclasses = BaseUsersApi.subclasses + (cls,)
    async def list_users(
        self,
    ) -> UserList:
        ...


    async def create_user(
        self,
        create_user_request: CreateUserRequest,
    ) -> UserSummary:
        ...


    async def reset_user_password(
        self,
        userId: StrictStr,
        reset_user_password_request: ResetUserPasswordRequest,
    ) -> None:
        ...


    async def add_user_role(
        self,
        userId: StrictStr,
        user_role_request: UserRoleRequest,
    ) -> None:
        ...


    async def remove_user_role(
        self,
        userId: StrictStr,
        role: StrictStr,
    ) -> None:
        ...


    async def update_user_status(
        self,
        userId: StrictStr,
        update_user_status_request: UpdateUserStatusRequest,
    ) -> None:
        ...
