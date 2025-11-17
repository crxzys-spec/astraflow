# coding: utf-8

from fastapi import Depends, HTTPException, Security, status  # noqa: F401
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

from scheduler_api.auth.context import set_current_token
from scheduler_api.auth.service import decode_access_token
from scheduler_api.models.extra_models import TokenModel


bearer_auth = HTTPBearer()


async def get_token_bearerAuth(credentials: HTTPAuthorizationCredentials = Depends(bearer_auth)) -> TokenModel:
    """
    Check and retrieve authentication information from custom bearer token.

    :param credentials Credentials provided by Authorization header
    :type credentials: HTTPAuthorizationCredentials
    :return: Decoded token information or None if token is invalid
    :rtype: TokenModel | None
    """
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "forbidden", "message": "Authentication required."},
        )
    authenticated = await decode_access_token(credentials.credentials)
    token = TokenModel(
        sub=str(authenticated.user_id),
        username=authenticated.username,
        display_name=authenticated.display_name,
        roles=list(authenticated.roles),
    )
    set_current_token(token)
    return token
