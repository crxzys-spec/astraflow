# coding: utf-8

from typing import ClassVar, Dict, List, Tuple  # noqa: F401

from scheduler_api.models.auth_login_request import AuthLoginRequest
from scheduler_api.models.auth_login_response1 import AuthLoginResponse1
from scheduler_api.models.error import Error


class BaseAuthApi:
    subclasses: ClassVar[Tuple] = ()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        BaseAuthApi.subclasses = BaseAuthApi.subclasses + (cls,)
    async def auth_login(
        self,
        auth_login_request: AuthLoginRequest,
    ) -> AuthLoginResponse1:
        ...
