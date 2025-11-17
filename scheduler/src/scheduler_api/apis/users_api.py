# coding: utf-8

from typing import Dict, List  # noqa: F401
import importlib
import pkgutil

from scheduler_api.apis.users_api_base import BaseUsersApi
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
from pydantic import StrictStr
from typing import Any
from scheduler_api.models.add_user_role_request import AddUserRoleRequest
from scheduler_api.models.create_user201_response import CreateUser201Response
from scheduler_api.models.create_user_request import CreateUserRequest
from scheduler_api.models.list_users200_response import ListUsers200Response
from scheduler_api.models.reset_user_password_request import ResetUserPasswordRequest
from scheduler_api.models.update_user_status_request import UpdateUserStatusRequest
from scheduler_api.security_api import get_token_bearerAuth

router = APIRouter()

ns_pkg = scheduler_api.impl
for _, name, _ in pkgutil.iter_modules(ns_pkg.__path__, ns_pkg.__name__ + "."):
    importlib.import_module(name)


@router.get(
    "/api/v1/users",
    responses={
        200: {"model": ListUsers200Response, "description": "OK"},
    },
    tags=["Users"],
    summary="List users and their roles",
    response_model_by_alias=True,
)
async def list_users(
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth
    ),
) -> ListUsers200Response:
    if not BaseUsersApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseUsersApi.subclasses[0]().list_users()


@router.post(
    "/api/v1/users",
    responses={
        201: {"model": CreateUser201Response, "description": "Created"},
    },
    tags=["Users"],
    summary="Create a new user",
    response_model_by_alias=True,
)
async def create_user(
    create_user_request: CreateUserRequest = Body(None, description=""),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth
    ),
) -> CreateUser201Response:
    if not BaseUsersApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseUsersApi.subclasses[0]().create_user(create_user_request)


@router.post(
    "/api/v1/users/{userId}/password",
    responses={
        204: {"description": "Password updated"},
    },
    tags=["Users"],
    summary="Reset user password",
    response_model_by_alias=True,
)
async def reset_user_password(
    userId: StrictStr = Path(..., description=""),
    reset_user_password_request: ResetUserPasswordRequest = Body(None, description=""),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth
    ),
) -> None:
    if not BaseUsersApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseUsersApi.subclasses[0]().reset_user_password(userId, reset_user_password_request)


@router.post(
    "/api/v1/users/{userId}/roles",
    responses={
        204: {"description": "Role assigned"},
    },
    tags=["Users"],
    summary="Assign role to user",
    response_model_by_alias=True,
)
async def add_user_role(
    userId: StrictStr = Path(..., description=""),
    add_user_role_request: AddUserRoleRequest = Body(None, description=""),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth
    ),
) -> None:
    if not BaseUsersApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseUsersApi.subclasses[0]().add_user_role(userId, add_user_role_request)


@router.delete(
    "/api/v1/users/{userId}/roles/{role}",
    responses={
        204: {"description": "Role removed"},
    },
    tags=["Users"],
    summary="Remove role from user",
    response_model_by_alias=True,
)
async def remove_user_role(
    userId: StrictStr = Path(..., description=""),
    role: StrictStr = Path(..., description=""),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth
    ),
) -> None:
    if not BaseUsersApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseUsersApi.subclasses[0]().remove_user_role(userId, role)


@router.patch(
    "/api/v1/users/{userId}/status",
    responses={
        204: {"description": "Status updated"},
    },
    tags=["Users"],
    summary="Toggle user active state",
    response_model_by_alias=True,
)
async def update_user_status(
    userId: StrictStr = Path(..., description=""),
    update_user_status_request: UpdateUserStatusRequest = Body(None, description=""),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth
    ),
) -> None:
    if not BaseUsersApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseUsersApi.subclasses[0]().update_user_status(userId, update_user_status_request)
