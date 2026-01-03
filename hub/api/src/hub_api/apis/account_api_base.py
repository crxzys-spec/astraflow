# coding: utf-8

from typing import ClassVar, Dict, List, Tuple  # noqa: F401

from hub_api.models.account import Account
from hub_api.models.error import Error
from hub_api.security_api import get_token_bearerAuth

class BaseAccountApi:
    subclasses: ClassVar[Tuple] = ()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        BaseAccountApi.subclasses = BaseAccountApi.subclasses + (cls,)
    async def get_account(
        self,
    ) -> Account:
        ...
