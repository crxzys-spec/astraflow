from __future__ import annotations

from hub_api.apis.account_api_base import BaseAccountApi
from hub_api.models.account import Account
from hub_api.services.account_service import AccountService

_service = AccountService()


class AccountApiImpl(BaseAccountApi):
    async def get_account(self) -> Account:
        return await _service.get_account()
