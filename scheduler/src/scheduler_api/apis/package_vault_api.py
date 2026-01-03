# coding: utf-8

from typing import Dict, List, Any  # noqa: F401
import importlib
import pkgutil

from scheduler_api.apis.package_vault_api_base import BasePackageVaultApi
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
from scheduler_api.models.error import Error
from scheduler_api.models.package_vault_list import PackageVaultList
from scheduler_api.models.package_vault_upsert_request import PackageVaultUpsertRequest
from scheduler_api.security_api import get_token_bearerAuth

router = APIRouter()

ns_pkg = scheduler_api.impl
for _, name, _ in pkgutil.iter_modules(ns_pkg.__path__, ns_pkg.__name__ + "."):
    importlib.import_module(name)


@router.get(
    "/api/v1/package-vault",
    responses={
        200: {"model": PackageVaultList, "description": "OK"},
    },
    tags=["PackageVault"],
    summary="List package vault entries",
    response_model_by_alias=True,
)
async def list_package_vault(
    package_name: StrictStr = Query(None, description="", alias="packageName"),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth
    ),
) -> PackageVaultList:
    if not BasePackageVaultApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BasePackageVaultApi.subclasses[0]().list_package_vault(package_name)


@router.put(
    "/api/v1/package-vault",
    responses={
        200: {"model": PackageVaultList, "description": "OK"},
        400: {"model": Error, "description": "Invalid input"},
    },
    tags=["PackageVault"],
    summary="Upsert package vault entries",
    response_model_by_alias=True,
)
async def upsert_package_vault(
    package_vault_upsert_request: PackageVaultUpsertRequest = Body(None, description=""),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth
    ),
) -> PackageVaultList:
    if not BasePackageVaultApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BasePackageVaultApi.subclasses[0]().upsert_package_vault(package_vault_upsert_request)


@router.delete(
    "/api/v1/package-vault/{packageName}/{key}",
    responses={
        204: {"description": "Deleted"},
        404: {"model": Error, "description": "Resource not found"},
    },
    tags=["PackageVault"],
    summary="Delete package vault entry",
    response_model_by_alias=True,
)
async def delete_package_vault_item(
    packageName: StrictStr = Path(..., description=""),
    key: StrictStr = Path(..., description=""),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth
    ),
) -> None:
    if not BasePackageVaultApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BasePackageVaultApi.subclasses[0]().delete_package_vault_item(packageName, key)
