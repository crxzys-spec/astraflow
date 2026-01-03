# coding: utf-8

from typing import ClassVar, Dict, List, Tuple  # noqa: F401

from hub_api.models.auth_login_request import AuthLoginRequest
from hub_api.models.auth_register_request import AuthRegisterRequest
from hub_api.models.auth_response import AuthResponse
from hub_api.models.error import Error


class BaseAuthApi:
    subclasses: ClassVar[Tuple] = ()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        BaseAuthApi.subclasses = BaseAuthApi.subclasses + (cls,)
    async def register_account(
        self,
        auth_register_request: AuthRegisterRequest,
    ) -> AuthResponse:
        ...


    async def login_account(
        self,
        auth_login_request: AuthLoginRequest,
    ) -> AuthResponse:
        ...
