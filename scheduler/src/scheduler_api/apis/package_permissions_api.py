# coding: utf-8

from typing import Dict, List, Any  # noqa: F401
import importlib
import pkgutil

from scheduler_api.apis.package_permissions_api_base import BasePackagePermissionsApi
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
from typing import Any, Optional
from scheduler_api.models.error import Error
from scheduler_api.models.package_permission import PackagePermission
from scheduler_api.models.package_permission_create_request import PackagePermissionCreateRequest
from scheduler_api.models.package_permission_list import PackagePermissionList
from scheduler_api.security_api import get_token_bearerAuth

router = APIRouter()

ns_pkg = scheduler_api.impl
for _, name, _ in pkgutil.iter_modules(ns_pkg.__path__, ns_pkg.__name__ + "."):
    importlib.import_module(name)


@router.get(
    "/api/v1/package-permissions",
    responses={
        200: {"model": PackagePermissionList, "description": "OK"},
    },
    tags=["PackagePermissions"],
    summary="List package permissions",
    response_model_by_alias=True,
)
async def list_package_permissions(
    package_name: Optional[StrictStr] = Query(None, description="", alias="packageName"),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth
    ),
) -> PackagePermissionList:
    if not BasePackagePermissionsApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BasePackagePermissionsApi.subclasses[0]().list_package_permissions(package_name)


@router.post(
    "/api/v1/package-permissions",
    responses={
        201: {"model": PackagePermission, "description": "Created"},
        400: {"model": Error, "description": "Invalid input"},
    },
    tags=["PackagePermissions"],
    summary="Grant package permissions",
    response_model_by_alias=True,
)
async def create_package_permission(
    package_permission_create_request: PackagePermissionCreateRequest = Body(None, description=""),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth
    ),
) -> PackagePermission:
    if not BasePackagePermissionsApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BasePackagePermissionsApi.subclasses[0]().create_package_permission(package_permission_create_request)


@router.delete(
    "/api/v1/package-permissions/{permissionId}",
    responses={
        204: {"description": "Deleted"},
        404: {"model": Error, "description": "Resource not found"},
    },
    tags=["PackagePermissions"],
    summary="Revoke package permission",
    response_model_by_alias=True,
)
async def delete_package_permission(
    permissionId: StrictStr = Path(..., description=""),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth
    ),
) -> None:
    if not BasePackagePermissionsApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BasePackagePermissionsApi.subclasses[0]().delete_package_permission(permissionId)
