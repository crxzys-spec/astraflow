from __future__ import annotations

from hub_api.apis.account_api_base import BaseAccountApi
from hub_api.models.account import Account
from hub_api.models.account_update_request import AccountUpdateRequest
from hub_api.models.organization_invite_list import OrganizationInviteList
from hub_api.services.account_service import AccountService

_service = AccountService()


class AccountApiImpl(BaseAccountApi):
    async def get_account(self) -> Account:
        return await _service.get_account()

    async def update_account(self, account_update_request: AccountUpdateRequest) -> Account:
        return await _service.update_account(account_update_request)

    async def list_account_invites(self) -> OrganizationInviteList:
        return await _service.list_account_invites()
