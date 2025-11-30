# coding: utf-8

from typing import Dict, List  # noqa: F401
import importlib
import pkgutil

from scheduler_api.apis.auth_api_base import BaseAuthApi
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
from scheduler_api.models.auth_login_request import AuthLoginRequest
from scheduler_api.models.auth_login_response import AuthLoginResponse
from scheduler_api.models.error import Error


router = APIRouter()

ns_pkg = scheduler_api.impl
for _, name, _ in pkgutil.iter_modules(ns_pkg.__path__, ns_pkg.__name__ + "."):
    importlib.import_module(name)


@router.post(
    "/api/v1/auth/login",
    responses={
        200: {"model": AuthLoginResponse, "description": "Authenticated"},
        401: {"model": Error, "description": "Authentication required or credentials invalid"},
    },
    tags=["Auth"],
    summary="Exchange username/password for a JWT",
    response_model_by_alias=True,
)
async def auth_login(
    auth_login_request: AuthLoginRequest = Body(None, description=""),
) -> AuthLoginResponse:
    if not BaseAuthApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseAuthApi.subclasses[0]().auth_login(auth_login_request)
