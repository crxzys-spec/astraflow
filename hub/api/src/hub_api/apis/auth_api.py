# coding: utf-8

from typing import Dict, List  # noqa: F401
import importlib
import pkgutil

from hub_api.apis.auth_api_base import BaseAuthApi
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
from hub_api.models.auth_login_request import AuthLoginRequest
from hub_api.models.auth_register_request import AuthRegisterRequest
from hub_api.models.auth_response import AuthResponse
from hub_api.models.error import Error


router = APIRouter()

ns_pkg = hub_api.impl
for _, name, _ in pkgutil.iter_modules(ns_pkg.__path__, ns_pkg.__name__ + "."):
    importlib.import_module(name)


@router.post(
    "/api/v1/auth/register",
    responses={
        201: {"model": AuthResponse, "description": "Created"},
        400: {"model": Error, "description": "Invalid input"},
        409: {"model": Error, "description": "Conflict"},
    },
    tags=["Auth"],
    summary="Register a new account",
    response_model_by_alias=True,
)
async def register_account(
    auth_register_request: AuthRegisterRequest = Body(None, description=""),
) -> AuthResponse:
    if not BaseAuthApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseAuthApi.subclasses[0]().register_account(auth_register_request)


@router.post(
    "/api/v1/auth/login",
    responses={
        200: {"model": AuthResponse, "description": "OK"},
        400: {"model": Error, "description": "Invalid input"},
        401: {"model": Error, "description": "Unauthorized"},
    },
    tags=["Auth"],
    summary="Login with username and password",
    response_model_by_alias=True,
)
async def login_account(
    auth_login_request: AuthLoginRequest = Body(None, description=""),
) -> AuthResponse:
    if not BaseAuthApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseAuthApi.subclasses[0]().login_account(auth_login_request)
