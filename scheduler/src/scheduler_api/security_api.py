# coding: utf-8

from __future__ import annotations

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from scheduler_api.auth.context import set_current_token
from scheduler_api.auth.service import decode_access_token
from scheduler_api.http.errors import unauthorized
from scheduler_api.models.extra_models import TokenModel


bearer_auth = HTTPBearer(auto_error=True)


async def get_token_bearerAuth(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_auth),
) -> TokenModel:
    """
    Decode and validate bearer tokens for protected endpoints.

    This helper also powers the ContextVar used by ``require_roles`` so downstream
    implementations can enforce RBAC without threading credentials through every call.
    """

    if credentials is None or not credentials.credentials:
        raise unauthorized("Missing bearer token")

    token_value = credentials.credentials
    token_model = await _resolve_token(token_value)
    set_current_token(token_model)
    return token_model


async def _resolve_token(token_value: str) -> TokenModel:
    user = await decode_access_token(token_value)
    return TokenModel(sub=user.user_id, roles=user.roles)
