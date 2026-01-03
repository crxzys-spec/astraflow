# coding: utf-8

from contextvars import ContextVar
from typing import List, Optional

from fastapi import Depends, Security  # noqa: F401
from fastapi.openapi.models import OAuthFlowImplicit, OAuthFlows  # noqa: F401
from fastapi.security import (  # noqa: F401
    HTTPAuthorizationCredentials,
    HTTPBasic,
    HTTPBasicCredentials,
    HTTPBearer,
    OAuth2,
    OAuth2AuthorizationCodeBearer,
    OAuth2PasswordBearer,
    SecurityScopes,
)
from fastapi.security.api_key import APIKeyCookie, APIKeyHeader, APIKeyQuery  # noqa: F401

from hub_api.models.extra_models import TokenModel


_SCOPES = {
    "read": "Read hub resources",
    "publish": "Publish or manage hub resources",
    "admin": "Administrative access",
}

oauth2_password = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    scopes=_SCOPES,
    auto_error=False,
)
_current_actor: ContextVar[Optional[str]] = ContextVar("hub_current_actor", default=None)
_current_scopes: ContextVar[List[str]] = ContextVar("hub_current_scopes", default=[])
_current_token: ContextVar[Optional[str]] = ContextVar("hub_current_token", default=None)


def get_token_bearerAuth(
    security_scopes: SecurityScopes, token: str = Depends(oauth2_password)
) -> TokenModel:
    """
    Validate and decode token.

    :param token Token provided by Authorization header
    :type token: str
    :return: Decoded token information or None if token is invalid
    :rtype: TokenModel | None
    """

    from fastapi import HTTPException, status
    from hub_api.repo.tokens import resolve_token

    if not token:
        if security_scopes.scopes:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
        _current_actor.set(None)
        _current_scopes.set([])
        _current_token.set(None)
        return TokenModel(sub="")

    try:
        actor_id, scopes = resolve_token(token)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized") from exc

    if security_scopes.scopes and "admin" not in scopes:
        missing = [scope for scope in security_scopes.scopes if scope not in scopes]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient scope to perform this action.",
            )

    _current_actor.set(actor_id)
    _current_scopes.set(scopes)
    _current_token.set(token)
    return TokenModel(sub=actor_id)


def validate_scope_bearerAuth(
    required_scopes: SecurityScopes, token_scopes: List[str]
) -> bool:
    """
    Validate required scopes are included in token scope

    :param required_scopes Required scope to access called API
    :type required_scopes: List[str]
    :param token_scopes Scope present in token
    :type token_scopes: List[str]
    :return: True if access to called API is allowed
    :rtype: bool
    """

    if "admin" in token_scopes:
        return True
    return all(scope in token_scopes for scope in required_scopes.scopes)


def get_current_actor() -> Optional[str]:
    return _current_actor.get()


def get_current_scopes() -> List[str]:
    return list(_current_scopes.get() or [])


def get_current_token_value() -> Optional[str]:
    return _current_token.get()


def require_actor() -> str:
    actor_id = get_current_actor()
    if not actor_id:
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    return actor_id


def is_admin() -> bool:
    return "admin" in set(get_current_scopes())


def require_scope(required: str) -> None:
    scopes = set(get_current_scopes())
    if "admin" in scopes:
        return
    if required not in scopes:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient scope to perform this action.",
        )
