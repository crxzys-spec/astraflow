# coding: utf-8

from typing import ClassVar, Dict, List, Tuple  # noqa: F401

from hub_api.models.account import Account
from hub_api.models.account_update_request import AccountUpdateRequest
from hub_api.models.error import Error
from hub_api.models.organization_invite_list import OrganizationInviteList
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


    async def update_account(
        self,
        account_update_request: AccountUpdateRequest,
    ) -> Account:
        ...


    async def list_account_invites(
        self,
    ) -> OrganizationInviteList:
        ...
