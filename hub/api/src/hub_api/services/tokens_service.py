from __future__ import annotations

from fastapi import HTTPException, status

from hub_api.repo.audit import record_audit_event
from hub_api.repo.accounts import get_account
from hub_api.repo.orgs import get_organization, get_org_role
from hub_api.repo.tokens import create_token, list_tokens, revoke_token
from hub_api.repo.packages import get_package_record
from hub_api.models.access_token import AccessToken
from hub_api.models.access_token_create_request import AccessTokenCreateRequest
from hub_api.models.access_token_list import AccessTokenList
from hub_api.security_api import get_current_scopes, is_admin, require_actor
from hub_api.services.permissions import get_package_role_for_user


def _normalize(value: str | None) -> str:
    return value.lower().strip() if value else ""


def _scope_values(scopes) -> list[str]:
    values = []
    for scope in scopes or []:
        values.append(scope.value if hasattr(scope, "value") else str(scope))
    return values


def _split_package_name(value: str) -> tuple[str | None, str]:
    raw = value.strip()
    if "/" in raw:
        owner, name = raw.split("/", 1)
        if owner and name:
            return owner, name
    return None, raw


def _resolve_owner_identifier(owner: str) -> str:
    account = get_account(owner)
    if account:
        return account["id"]
    org = get_organization(owner)
    if org:
        return org["id"]
    raise HTTPException(status_code=404, detail="Not Found")


def _resolve_owner_namespace(owner_id: str) -> str:
    account = get_account(owner_id) or {}
    if account:
        return account.get("username") or owner_id
    org = get_organization(owner_id)
    if org:
        return org.get("slug") or org.get("id") or owner_id
    return owner_id


def _token_from_record(record: dict, include_secret: bool) -> AccessToken:
    payload = dict(record)
    if not include_secret:
        payload["token"] = None
    return AccessToken.from_dict(payload)


class TokensService:
    async def list_tokens(self) -> AccessTokenList:
        actor_id = require_actor()
        tokens = list_tokens(actor_id)
        items = [_token_from_record(token, include_secret=False) for token in tokens]
        return AccessTokenList(items=items)

    async def create_publish_token(
        self,
        access_token_create_request: AccessTokenCreateRequest,
    ) -> AccessToken:
        actor_id = require_actor()
        if access_token_create_request is None:
            raise HTTPException(status_code=400, detail="Payload is required.")
        requested_scopes = _scope_values(access_token_create_request.scopes)
        if not requested_scopes:
            raise HTTPException(status_code=400, detail="Scopes are required.")
        current_scopes = set(get_current_scopes())
        if "admin" not in current_scopes and not set(requested_scopes).issubset(current_scopes):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        package_name = access_token_create_request.package_name
        org_id = getattr(access_token_create_request, "org_id", None)
        if org_id:
            org = get_organization(org_id)
            if not org:
                raise HTTPException(status_code=404, detail="Not Found")
            if not is_admin() and get_org_role(org_id, actor_id) not in ("owner", "admin"):
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        resolved_package_name = package_name
        if package_name:
            owner_hint, package_only = _split_package_name(package_name)
            if owner_hint:
                owner_id = _resolve_owner_identifier(owner_hint)
            elif org_id:
                owner_id = org_id
            else:
                owner_id = actor_id
            if org_id and _normalize(owner_id) != _normalize(org_id):
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
            package_record = get_package_record(owner_id, package_only)
            if not package_record:
                raise HTTPException(status_code=404, detail="Not Found")
            role = get_package_role_for_user(owner_id, package_only, actor_id)
            if role not in ("write", "maintainer", "owner") and not is_admin():
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
            resolved_package_name = f"{_resolve_owner_namespace(owner_id)}/{package_only}"
        token = create_token(
            owner_id=actor_id,
            label=access_token_create_request.label,
            scopes=requested_scopes,
            package_name=resolved_package_name,
            org_id=org_id,
            expires_at=access_token_create_request.expires_at,
        )
        record_audit_event(
            action="token.create",
            actor_id=actor_id,
            target_type="token",
            target_id=token.get("id"),
            metadata={
                "scopes": requested_scopes,
                "packageName": resolved_package_name,
                "orgId": org_id,
                "label": access_token_create_request.label,
            },
        )
        return _token_from_record(token, include_secret=True)

    async def revoke_token(
        self,
        tokenId: str,
    ) -> None:
        actor_id = require_actor()
        try:
            revoke_token(tokenId, actor_id)
        except ValueError as exc:
            if str(exc) == "token_not_found":
                raise HTTPException(status_code=404, detail="Not Found") from exc
            if str(exc) == "token_owner_mismatch":
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden") from exc
            raise HTTPException(status_code=400, detail="Unable to revoke token.") from exc
        record_audit_event(
            action="token.revoke",
            actor_id=actor_id,
            target_type="token",
            target_id=tokenId,
            metadata=None,
        )
        return None
