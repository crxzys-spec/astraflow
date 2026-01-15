# coding: utf-8

from typing import Dict, List  # noqa: F401
import importlib
import pkgutil

from hub_api.apis.account_api_base import BaseAccountApi
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
from hub_api.models.account import Account
from hub_api.models.account_update_request import AccountUpdateRequest
from hub_api.models.error import Error
from hub_api.models.organization_invite_list import OrganizationInviteList
from hub_api.security_api import get_token_bearerAuth

router = APIRouter()

ns_pkg = hub_api.impl
for _, name, _ in pkgutil.iter_modules(ns_pkg.__path__, ns_pkg.__name__ + "."):
    importlib.import_module(name)


@router.get(
    "/api/v1/account",
    responses={
        200: {"model": Account, "description": "OK"},
        401: {"model": Error, "description": "Unauthorized"},
    },
    tags=["Account"],
    summary="Get current account",
    response_model_by_alias=True,
)
async def get_account(
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth, scopes=["read"]
    ),
) -> Account:
    if not BaseAccountApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseAccountApi.subclasses[0]().get_account()


@router.patch(
    "/api/v1/account",
    responses={
        200: {"model": Account, "description": "OK"},
        400: {"model": Error, "description": "Invalid input"},
        401: {"model": Error, "description": "Unauthorized"},
    },
    tags=["Account"],
    summary="Update current account",
    response_model_by_alias=True,
)
async def update_account(
    account_update_request: AccountUpdateRequest = Body(None, description=""),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth, scopes=["read"]
    ),
) -> Account:
    if not BaseAccountApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseAccountApi.subclasses[0]().update_account(account_update_request)


@router.get(
    "/api/v1/account/invites",
    responses={
        200: {"model": OrganizationInviteList, "description": "OK"},
        401: {"model": Error, "description": "Unauthorized"},
    },
    tags=["Account"],
    summary="List account invites",
    response_model_by_alias=True,
)
async def list_account_invites(
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth, scopes=["read"]
    ),
) -> OrganizationInviteList:
    if not BaseAccountApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseAccountApi.subclasses[0]().list_account_invites()
