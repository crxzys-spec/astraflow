from __future__ import annotations

from fastapi import HTTPException, status

from hub_api.repo.accounts import get_account, update_account
from hub_api.repo.orgs import list_user_invites
from hub_api.models.account import Account
from hub_api.models.account_update_request import AccountUpdateRequest
from hub_api.models.organization_invite import OrganizationInvite
from hub_api.models.organization_invite_list import OrganizationInviteList
from hub_api.security_api import require_actor
from hub_api.repo.audit import record_audit_event


class AccountService:
    async def get_account(self) -> Account:
        actor_id = require_actor()
        record = get_account(actor_id)
        if not record:
            raise HTTPException(status_code=404, detail="Not Found")
        return Account.from_dict(record)

    async def list_account_invites(self) -> OrganizationInviteList:
        actor_id = require_actor()
        invites = [OrganizationInvite.from_dict(record) for record in list_user_invites(actor_id)]
        return OrganizationInviteList(items=invites)

    async def update_account(self, account_update_request: AccountUpdateRequest) -> Account:
        actor_id = require_actor()
        if account_update_request is None:
            raise HTTPException(status_code=400, detail="Payload is required.")
        display_name = getattr(account_update_request, "display_name", None) or getattr(
            account_update_request, "displayName", None
        )
        email = getattr(account_update_request, "email", None)
        if display_name is not None:
            display_name = display_name.strip()
        if email is not None:
            email = email.strip()
        if display_name == "":
            raise HTTPException(status_code=400, detail="displayName cannot be empty.")
        if email == "":
            raise HTTPException(status_code=400, detail="email cannot be empty.")
        if display_name is None and email is None:
            raise HTTPException(status_code=400, detail="No changes provided.")
        updated = update_account(
            actor_id,
            display_name=display_name,
            email=email,
        )
        if not updated:
            raise HTTPException(status_code=404, detail="Not Found")
        record_audit_event(
            action="account.update",
            actor_id=actor_id,
            target_type="account",
            target_id=actor_id,
            metadata={"displayName": display_name, "email": email},
        )
        return Account.from_dict(updated)
