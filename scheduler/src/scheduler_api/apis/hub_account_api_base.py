# coding: utf-8

from typing import ClassVar, Dict, List, Tuple  # noqa: F401

from scheduler_api.models.error import Error
from scheduler_api.models.hub_account import HubAccount
from scheduler_api.security_api import get_token_bearerAuth

class BaseHubAccountApi:
    subclasses: ClassVar[Tuple] = ()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        BaseHubAccountApi.subclasses = BaseHubAccountApi.subclasses + (cls,)
    async def get_hub_account(
        self,
    ) -> HubAccount:
        ...
