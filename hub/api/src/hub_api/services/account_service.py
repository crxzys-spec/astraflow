from __future__ import annotations

from fastapi import HTTPException, status

from hub_api.repo.accounts import get_account
from hub_api.models.account import Account
from hub_api.security_api import require_actor


class AccountService:
    async def get_account(self) -> Account:
        actor_id = require_actor()
        record = get_account(actor_id)
        if not record:
            raise HTTPException(status_code=404, detail="Not Found")
        return Account.from_dict(record)
