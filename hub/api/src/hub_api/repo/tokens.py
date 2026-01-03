from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import select

from hub_api.db.models import HubToken
from hub_api.db.session import SessionLocal
from hub_api.repo.common import _generate_id, _now
from hub_api.repo.state import _TOKEN_BY_SECRET, _TOKENS, _USERS

DEFAULT_OWNER_ID = "hub-user"

DEFAULT_OWNER_NAME = "Hub Publisher"

DEFAULT_SCOPES = ["read", "publish", "admin"]

def _token_from_model(token: HubToken) -> dict[str, Any]:
    return {
        "id": token.id,
        "label": token.label,
        "scopes": list(token.scopes or []),
        "packageName": token.package_name,
        "createdAt": token.created_at,
        "lastUsedAt": token.last_used_at,
        "expiresAt": token.expires_at,
        "ownerId": token.owner_id,
        "token": token.token,
    }

def list_tokens(user_id: str) -> list[dict[str, Any]]:
    with SessionLocal() as session:
        tokens = session.execute(
            select(HubToken).where(HubToken.owner_id == user_id)
        ).scalars()
        return [_token_from_model(token) for token in tokens]

def create_token(
    *,
    owner_id: str,
    label: str,
    scopes: list[str],
    package_name: str | None,
    expires_at: datetime | None,
) -> dict[str, Any]:
    token_id = _generate_id()
    secret = f"tok_{uuid4().hex}"
    with SessionLocal() as session:
        record = HubToken(
            id=token_id,
            owner_id=owner_id,
            label=label,
            scopes=scopes,
            package_name=package_name,
            expires_at=expires_at,
            token=secret,
        )
        session.add(record)
        session.commit()
        session.refresh(record)
    return _token_from_model(record)

def revoke_token(token_id: str, actor_id: str) -> None:
    with SessionLocal() as session:
        token = session.get(HubToken, token_id)
        if not token:
            raise ValueError("token_not_found")
        if token.owner_id != actor_id:
            raise ValueError("token_owner_mismatch")
        token_secret = token.token
        session.delete(token)
        session.commit()
        if token_secret:
            _TOKEN_BY_SECRET.pop(token_secret, None)
        _TOKENS.pop(token_id, None)

def resolve_token(token_value: str) -> tuple[str, list[str]]:
    with SessionLocal() as session:
        token = session.execute(
            select(HubToken).where(HubToken.token == token_value)
        ).scalar_one_or_none()
        if token:
            if token.expires_at and token.expires_at < _now():
                raise ValueError("invalid_token")
            token.last_used_at = _now()
            session.commit()
            return token.owner_id, list(token.scopes or [])

    if token_value in _TOKEN_BY_SECRET:
        token_id = _TOKEN_BY_SECRET[token_value]
        token = _TOKENS.get(token_id)
        if not token:
            raise ValueError("invalid_token")
        token["lastUsedAt"] = _now()
        return token["ownerId"], token["scopes"]
    if token_value in _USERS:
        return token_value, DEFAULT_SCOPES
    if token_value == DEFAULT_OWNER_ID:
        return DEFAULT_OWNER_ID, DEFAULT_SCOPES
    raise ValueError("invalid_token")

def get_token_record(token_value: str) -> dict[str, Any] | None:
    with SessionLocal() as session:
        token = session.execute(
            select(HubToken).where(HubToken.token == token_value)
        ).scalar_one_or_none()
        if token is not None:
            return _token_from_model(token)
    token_id = _TOKEN_BY_SECRET.get(token_value)
    if not token_id:
        return None
    return _TOKENS.get(token_id)
