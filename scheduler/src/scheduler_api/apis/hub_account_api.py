# coding: utf-8

from typing import Dict, List  # noqa: F401
import importlib
import pkgutil

from scheduler_api.apis.hub_account_api_base import BaseHubAccountApi
import scheduler_api.impl

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

from scheduler_api.models.extra_models import TokenModel  # noqa: F401
from scheduler_api.models.error import Error
from scheduler_api.models.hub_account import HubAccount
from scheduler_api.security_api import get_token_bearerAuth

router = APIRouter()

ns_pkg = scheduler_api.impl
for _, name, _ in pkgutil.iter_modules(ns_pkg.__path__, ns_pkg.__name__ + "."):
    importlib.import_module(name)


@router.get(
    "/api/v1/hub/account",
    responses={
        200: {"model": HubAccount, "description": "OK"},
        401: {"model": Error, "description": "Authentication required or credentials invalid"},
        403: {"model": Error, "description": "Authenticated but lacks required permissions"},
        400: {"model": Error, "description": "Invalid input"},
    },
    tags=["HubAccount"],
    summary="Get hub account profile via scheduler proxy",
    response_model_by_alias=True,
)
async def get_hub_account(
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth
    ),
) -> HubAccount:
    if not BaseHubAccountApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseHubAccountApi.subclasses[0]().get_hub_account()
