# coding: utf-8

from typing import Dict, List, Any  # noqa: F401
import importlib
import pkgutil

from hub_api.apis.tokens_api_base import BaseTokensApi
import hub_api.impl

from fastapi import (  # noqa: F401
    APIRouter,
    Body,
    Cookie,
    Depends,
    Form,
    Header,
    HTTPException,
    Path,
    Query,
    Response,
    Security,
    status,
)

from hub_api.models.extra_models import TokenModel  # noqa: F401
from pydantic import StrictStr
from typing import Any
from hub_api.models.access_token import AccessToken
from hub_api.models.access_token_create_request import AccessTokenCreateRequest
from hub_api.models.access_token_list import AccessTokenList
from hub_api.models.error import Error
from hub_api.security_api import get_token_bearerAuth

router = APIRouter()

ns_pkg = hub_api.impl
for _, name, _ in pkgutil.iter_modules(ns_pkg.__path__, ns_pkg.__name__ + "."):
    importlib.import_module(name)


@router.get(
    "/api/v1/tokens",
    responses={
        200: {"model": AccessTokenList, "description": "OK"},
        401: {"model": Error, "description": "Unauthorized"},
    },
    tags=["Tokens"],
    summary="List access tokens",
    response_model_by_alias=True,
)
async def list_tokens(
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth, scopes=["publish"]
    ),
) -> AccessTokenList:
    if not BaseTokensApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseTokensApi.subclasses[0]().list_tokens()


@router.post(
    "/api/v1/tokens/publish",
    responses={
        201: {"model": AccessToken, "description": "Created"},
        400: {"model": Error, "description": "Invalid input"},
        401: {"model": Error, "description": "Unauthorized"},
    },
    tags=["Tokens"],
    summary="Create publish token",
    response_model_by_alias=True,
)
async def create_publish_token(
    access_token_create_request: AccessTokenCreateRequest = Body(None, description=""),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth, scopes=["publish"]
    ),
) -> AccessToken:
    if not BaseTokensApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseTokensApi.subclasses[0]().create_publish_token(access_token_create_request)


@router.delete(
    "/api/v1/tokens/{tokenId}",
    responses={
        204: {"description": "Deleted"},
        401: {"model": Error, "description": "Unauthorized"},
        404: {"model": Error, "description": "Not Found"},
    },
    tags=["Tokens"],
    summary="Revoke access token",
    response_model_by_alias=True,
)
async def revoke_token(
    tokenId: StrictStr = Path(..., description=""),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth, scopes=["publish"]
    ),
) -> None:
    if not BaseTokensApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseTokensApi.subclasses[0]().revoke_token(tokenId)
