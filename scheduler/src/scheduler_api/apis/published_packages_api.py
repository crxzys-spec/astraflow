# coding: utf-8

from typing import Dict, List, Any  # noqa: F401
import importlib
import pkgutil

from scheduler_api.apis.published_packages_api_base import BasePublishedPackagesApi
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
    File,
    UploadFile,
)

from scheduler_api.models.extra_models import TokenModel  # noqa: F401
from pydantic import Field, StrictBytes, StrictStr
from typing import Any, Optional, Tuple, Union
from typing_extensions import Annotated
from scheduler_api.models.error import Error
from scheduler_api.models.package_detail import PackageDetail
from scheduler_api.models.package_list import PackageList
from scheduler_api.models.published_package_gc_request import PublishedPackageGcRequest
from scheduler_api.models.published_package_gc_result import PublishedPackageGcResult
from scheduler_api.models.published_package_registry import PublishedPackageRegistry
from scheduler_api.models.published_package_reserve_request import PublishedPackageReserveRequest
from scheduler_api.models.published_package_status_request import PublishedPackageStatusRequest
from scheduler_api.models.published_package_tag_request import PublishedPackageTagRequest
from scheduler_api.models.published_package_transfer_request import PublishedPackageTransferRequest
from scheduler_api.models.published_package_visibility_request import PublishedPackageVisibilityRequest
from scheduler_api.security_api import get_token_bearerAuth

router = APIRouter()

ns_pkg = scheduler_api.impl
for _, name, _ in pkgutil.iter_modules(ns_pkg.__path__, ns_pkg.__name__ + "."):
    importlib.import_module(name)


@router.get(
    "/api/v1/published-packages",
    responses={
        200: {"model": PackageList, "description": "OK"},
    },
    tags=["PublishedPackages"],
    summary="List published packages",
    response_model_by_alias=True,
)
async def list_published_packages(
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth
    ),
) -> PackageList:
    if not BasePublishedPackagesApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BasePublishedPackagesApi.subclasses[0]().list_published_packages()


@router.post(
    "/api/v1/published-packages",
    responses={
        200: {"model": PackageDetail, "description": "OK"},
        400: {"model": Error, "description": "Invalid input"},
        409: {"model": Error, "description": "Conflict (e.g., idempotency-key reuse with different body)"},
    },
    tags=["PublishedPackages"],
    summary="Upload a published package archive",
    response_model_by_alias=True,
)
async def upload_published_package(
    file: UploadFile = File(None, description=""),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth
    ),
) -> PackageDetail:
    if not BasePublishedPackagesApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BasePublishedPackagesApi.subclasses[0]().upload_published_package(file)


@router.post(
    "/api/v1/published-packages/gc",
    responses={
        200: {"model": PublishedPackageGcResult, "description": "OK"},
        400: {"model": Error, "description": "Invalid input"},
        403: {"model": Error, "description": "Authenticated but lacks required permissions"},
    },
    tags=["PublishedPackages"],
    summary="Garbage collect published package versions",
    response_model_by_alias=True,
)
async def gc_published_packages(
    published_package_gc_request: PublishedPackageGcRequest = Body(None, description=""),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth
    ),
) -> PublishedPackageGcResult:
    if not BasePublishedPackagesApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BasePublishedPackagesApi.subclasses[0]().gc_published_packages(published_package_gc_request)


@router.get(
    "/api/v1/published-packages/{packageName}",
    responses={
        200: {"model": PackageDetail, "description": "OK"},
        404: {"model": Error, "description": "Resource not found"},
    },
    tags=["PublishedPackages"],
    summary="Get published package detail",
    response_model_by_alias=True,
)
async def get_published_package(
    packageName: StrictStr = Path(..., description=""),
    version: Annotated[Optional[StrictStr], Field(description="Specific package version to retrieve. Defaults to the latest available version.")] = Query(None, description="Specific package version to retrieve. Defaults to the latest available version.", alias="version"),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth
    ),
) -> PackageDetail:
    if not BasePublishedPackagesApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BasePublishedPackagesApi.subclasses[0]().get_published_package(packageName, version)


@router.get(
    "/api/v1/published-packages/{packageName}/registry",
    responses={
        200: {"model": PublishedPackageRegistry, "description": "OK"},
        403: {"model": Error, "description": "Authenticated but lacks required permissions"},
        404: {"model": Error, "description": "Resource not found"},
    },
    tags=["PublishedPackages"],
    summary="Get published package registry metadata",
    response_model_by_alias=True,
)
async def get_published_package_registry(
    packageName: StrictStr = Path(..., description=""),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth
    ),
) -> PublishedPackageRegistry:
    if not BasePublishedPackagesApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BasePublishedPackagesApi.subclasses[0]().get_published_package_registry(packageName)


@router.get(
    "/api/v1/published-packages/{packageName}/archive",
    responses={
        200: {"model": Any, "description": "OK"},
        404: {"model": Error, "description": "Resource not found"},
    },
    tags=["PublishedPackages"],
    summary="Download published package archive",
    response_model_by_alias=True,
)
async def download_published_package(
    packageName: StrictStr = Path(..., description=""),
    version: Annotated[Optional[StrictStr], Field(description="Specific package version to retrieve. Defaults to the latest available version.")] = Query(None, description="Specific package version to retrieve. Defaults to the latest available version.", alias="version"),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth
    ),
) -> Any:
    if not BasePublishedPackagesApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BasePublishedPackagesApi.subclasses[0]().download_published_package(packageName, version)


@router.post(
    "/api/v1/published-packages/{packageName}/reserve",
    responses={
        200: {"model": PublishedPackageRegistry, "description": "OK"},
        400: {"model": Error, "description": "Invalid input"},
        403: {"model": Error, "description": "Authenticated but lacks required permissions"},
        409: {"model": Error, "description": "Conflict (e.g., idempotency-key reuse with different body)"},
    },
    tags=["PublishedPackages"],
    summary="Reserve a published package name",
    response_model_by_alias=True,
)
async def reserve_published_package(
    packageName: StrictStr = Path(..., description=""),
    published_package_reserve_request: Optional[PublishedPackageReserveRequest] = Body(None, description=""),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth
    ),
) -> PublishedPackageRegistry:
    if not BasePublishedPackagesApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BasePublishedPackagesApi.subclasses[0]().reserve_published_package(packageName, published_package_reserve_request)


@router.patch(
    "/api/v1/published-packages/{packageName}/versions/{version}",
    responses={
        200: {"model": PackageDetail, "description": "OK"},
        400: {"model": Error, "description": "Invalid input"},
        403: {"model": Error, "description": "Authenticated but lacks required permissions"},
        404: {"model": Error, "description": "Resource not found"},
    },
    tags=["PublishedPackages"],
    summary="Set published package version status",
    response_model_by_alias=True,
)
async def set_published_package_version_status(
    packageName: StrictStr = Path(..., description=""),
    version: StrictStr = Path(..., description=""),
    published_package_status_request: PublishedPackageStatusRequest = Body(None, description=""),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth
    ),
) -> PackageDetail:
    if not BasePublishedPackagesApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BasePublishedPackagesApi.subclasses[0]().set_published_package_version_status(packageName, version, published_package_status_request)


@router.put(
    "/api/v1/published-packages/{packageName}/tags/{tag}",
    responses={
        204: {"description": "Updated"},
        400: {"model": Error, "description": "Invalid input"},
        403: {"model": Error, "description": "Authenticated but lacks required permissions"},
        404: {"model": Error, "description": "Resource not found"},
    },
    tags=["PublishedPackages"],
    summary="Set published package dist-tag",
    response_model_by_alias=True,
)
async def set_published_package_tag(
    packageName: StrictStr = Path(..., description=""),
    tag: StrictStr = Path(..., description=""),
    published_package_tag_request: PublishedPackageTagRequest = Body(None, description=""),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth
    ),
) -> None:
    if not BasePublishedPackagesApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BasePublishedPackagesApi.subclasses[0]().set_published_package_tag(packageName, tag, published_package_tag_request)


@router.delete(
    "/api/v1/published-packages/{packageName}/tags/{tag}",
    responses={
        204: {"description": "Deleted"},
        403: {"model": Error, "description": "Authenticated but lacks required permissions"},
        404: {"model": Error, "description": "Resource not found"},
    },
    tags=["PublishedPackages"],
    summary="Delete published package dist-tag",
    response_model_by_alias=True,
)
async def delete_published_package_tag(
    packageName: StrictStr = Path(..., description=""),
    tag: StrictStr = Path(..., description=""),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth
    ),
) -> None:
    if not BasePublishedPackagesApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BasePublishedPackagesApi.subclasses[0]().delete_published_package_tag(packageName, tag)


@router.patch(
    "/api/v1/published-packages/{packageName}/visibility",
    responses={
        200: {"model": PublishedPackageRegistry, "description": "OK"},
        400: {"model": Error, "description": "Invalid input"},
        403: {"model": Error, "description": "Authenticated but lacks required permissions"},
        404: {"model": Error, "description": "Resource not found"},
    },
    tags=["PublishedPackages"],
    summary="Update published package visibility",
    response_model_by_alias=True,
)
async def update_published_package_visibility(
    packageName: StrictStr = Path(..., description=""),
    published_package_visibility_request: PublishedPackageVisibilityRequest = Body(None, description=""),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth
    ),
) -> PublishedPackageRegistry:
    if not BasePublishedPackagesApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BasePublishedPackagesApi.subclasses[0]().update_published_package_visibility(packageName, published_package_visibility_request)


@router.post(
    "/api/v1/published-packages/{packageName}/transfer",
    responses={
        200: {"model": PublishedPackageRegistry, "description": "OK"},
        400: {"model": Error, "description": "Invalid input"},
        403: {"model": Error, "description": "Authenticated but lacks required permissions"},
        404: {"model": Error, "description": "Resource not found"},
    },
    tags=["PublishedPackages"],
    summary="Transfer published package ownership",
    response_model_by_alias=True,
)
async def transfer_published_package(
    packageName: StrictStr = Path(..., description=""),
    published_package_transfer_request: PublishedPackageTransferRequest = Body(None, description=""),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth
    ),
) -> PublishedPackageRegistry:
    if not BasePublishedPackagesApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BasePublishedPackagesApi.subclasses[0]().transfer_published_package(packageName, published_package_transfer_request)
