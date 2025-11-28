# coding: utf-8

from typing import Dict, List  # noqa: F401
import importlib
import pkgutil

from scheduler_api.apis.packages_api_base import BasePackagesApi
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
from pydantic import Field, StrictStr
from typing import Optional
from typing_extensions import Annotated
from scheduler_api.models.error import Error
from scheduler_api.models.package_detail1 import PackageDetail1
from scheduler_api.models.package_list1 import PackageList1
from scheduler_api.security_api import get_token_bearerAuth

router = APIRouter()

ns_pkg = scheduler_api.impl
for _, name, _ in pkgutil.iter_modules(ns_pkg.__path__, ns_pkg.__name__ + "."):
    importlib.import_module(name)


@router.get(
    "/api/v1/packages",
    responses={
        200: {"model": PackageList1, "description": "OK"},
    },
    tags=["Packages"],
    summary="List available packages",
    response_model_by_alias=True,
)
async def list_packages(
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth
    ),
) -> PackageList1:
    if not BasePackagesApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BasePackagesApi.subclasses[0]().list_packages()


@router.get(
    "/api/v1/packages/{packageName}",
    responses={
        200: {"model": PackageDetail1, "description": "OK"},
        404: {"model": Error, "description": "Resource not found"},
    },
    tags=["Packages"],
    summary="Get package detail",
    response_model_by_alias=True,
)
async def get_package(
    packageName: StrictStr = Path(..., description=""),
    version: Annotated[Optional[StrictStr], Field(description="Specific package version to retrieve. Defaults to the latest available version.")] = Query(None, description="Specific package version to retrieve. Defaults to the latest available version.", alias="version"),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth
    ),
) -> PackageDetail1:
    if not BasePackagesApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BasePackagesApi.subclasses[0]().get_package(packageName, version)
