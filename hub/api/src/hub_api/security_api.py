# coding: utf-8

from contextvars import ContextVar
import logging
from typing import List, Optional

from fastapi import Depends, Header, Request, Security  # noqa: F401
from fastapi.concurrency import run_in_threadpool
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
from fastapi.security.utils import get_authorization_scheme_param

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
_current_org: ContextVar[Optional[str]] = ContextVar("hub_current_org", default=None)
_logged_db_url = False
_logger = logging.getLogger(__name__)


def _mask_token(token_value: str) -> str:
    if not token_value:
        return ""
    if len(token_value) <= 8:
        return token_value
    return f"{token_value[:4]}...{token_value[-4:]}"


def _expand_scopes(scopes: list[str]) -> list[str]:
    expanded = set(scopes or [])
    if "publish" in expanded:
        expanded.add("read")
    return list(expanded)


async def get_token_bearerAuth(
    security_scopes: SecurityScopes,
    token: str = Depends(oauth2_password),
    authorization: Optional[str] = Header(default=None),
    request: Request = None,
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

    global _logged_db_url
    if not _logged_db_url:
        from hub_api.db.session import DATABASE_URL

        _logger.info("Hub auth using DATABASE_URL=%s", DATABASE_URL)
        _logged_db_url = True

    token_value = token
    if not token_value and authorization:
        scheme, param = get_authorization_scheme_param(authorization)
        if scheme.lower() == "bearer":
            token_value = param

    if not token_value:
        _logger.info("Hub auth missing token scopes=%s", security_scopes.scopes)
        if security_scopes.scopes:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
        _current_actor.set(None)
        _current_scopes.set([])
        _current_token.set(None)
        _current_org.set(None)
        return TokenModel(sub="")

    client_ip = None
    user_agent = None
    if request is not None:
        if request.client:
            client_ip = request.client.host
        user_agent = request.headers.get("user-agent")
    try:
        actor_id, scopes, org_id = await run_in_threadpool(
            resolve_token, token_value, client_ip, user_agent
        )
    except ValueError as exc:
        _logger.warning("Hub auth invalid token=%s", _mask_token(token_value))
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized") from exc

    expanded_scopes = _expand_scopes(scopes)
    if security_scopes.scopes and "admin" not in expanded_scopes:
        missing = [scope for scope in security_scopes.scopes if scope not in expanded_scopes]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient scope to perform this action.",
            )

    _logger.info("Hub auth ok actor=%s scopes=%s", actor_id, expanded_scopes)
    _current_actor.set(actor_id)
    _current_scopes.set(expanded_scopes)
    _current_token.set(token_value)
    _current_org.set(org_id)
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

    expanded_scopes = set(_expand_scopes(token_scopes))
    if "admin" in expanded_scopes:
        return True
    return all(scope in expanded_scopes for scope in required_scopes.scopes)


def get_current_actor() -> Optional[str]:
    return _current_actor.get()


def get_current_scopes() -> List[str]:
    return list(_current_scopes.get() or [])


def get_current_token_value() -> Optional[str]:
    return _current_token.get()


def get_current_org_id() -> Optional[str]:
    return _current_org.get()


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
