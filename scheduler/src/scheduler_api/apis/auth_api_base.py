# coding: utf-8

from typing import ClassVar, Dict, List, Tuple  # noqa: F401

from scheduler_api.models.auth_login200_response import AuthLogin200Response
from scheduler_api.models.auth_login401_response import AuthLogin401Response
from scheduler_api.models.auth_login_request import AuthLoginRequest


class BaseAuthApi:
    subclasses: ClassVar[Tuple] = ()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        BaseAuthApi.subclasses = BaseAuthApi.subclasses + (cls,)
    async def auth_login(
        self,
        auth_login_request: AuthLoginRequest,
    ) -> AuthLogin200Response:
        ...
