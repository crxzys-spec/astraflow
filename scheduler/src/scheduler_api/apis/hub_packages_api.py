# coding: utf-8

from typing import Dict, List, Any  # noqa: F401
import importlib
import pkgutil

from scheduler_api.apis.hub_packages_api_base import BaseHubPackagesApi
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
from typing import List, Optional, Tuple, Union
from typing_extensions import Annotated
from scheduler_api.models.error import Error
from scheduler_api.models.hub_package_detail import HubPackageDetail
from scheduler_api.models.hub_package_install_request import HubPackageInstallRequest
from scheduler_api.models.hub_package_install_response import HubPackageInstallResponse
from scheduler_api.models.hub_package_list_response import HubPackageListResponse
from scheduler_api.models.hub_package_version_detail import HubPackageVersionDetail
from scheduler_api.models.hub_visibility import HubVisibility
from scheduler_api.security_api import get_token_bearerAuth

router = APIRouter()

ns_pkg = scheduler_api.impl
for _, name, _ in pkgutil.iter_modules(ns_pkg.__path__, ns_pkg.__name__ + "."):
    importlib.import_module(name)


@router.get(
    "/api/v1/hub/packages",
    responses={
        200: {"model": HubPackageListResponse, "description": "OK"},
    },
    tags=["HubPackages"],
    summary="List hub packages",
    response_model_by_alias=True,
)
async def list_hub_packages(
    q: Annotated[Optional[StrictStr], Field(description="Search query")] = Query(None, description="Search query", alias="q"),
    tag: Annotated[Optional[StrictStr], Field(description="Filter by tag")] = Query(None, description="Filter by tag", alias="tag"),
    owner: Annotated[Optional[StrictStr], Field(description="Filter by owner id")] = Query(None, description="Filter by owner id", alias="owner"),
    page: Annotated[Optional[Annotated[int, Field(ge=1)]], Field(description="1-based page index")] = Query(1, description="1-based page index", alias="page", ge=1),
    page_size: Annotated[Optional[Annotated[int, Field(le=200, ge=1)]], Field(description="Page size")] = Query(20, description="Page size", alias="pageSize", ge=1, le=200),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth
    ),
) -> HubPackageListResponse:
    if not BaseHubPackagesApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseHubPackagesApi.subclasses[0]().list_hub_packages(q, tag, owner, page, page_size)


@router.post(
    "/api/v1/hub/packages",
    responses={
        201: {"model": HubPackageVersionDetail, "description": "Created"},
        400: {"model": Error, "description": "Invalid input"},
        401: {"model": Error, "description": "Authentication required or credentials invalid"},
        403: {"model": Error, "description": "Authenticated but lacks required permissions"},
        409: {"model": Error, "description": "Conflict (e.g., idempotency-key reuse with different body)"},
    },
    tags=["HubPackages"],
    summary="Publish a package archive to Hub",
    response_model_by_alias=True,
)
async def publish_hub_package(
    file: UploadFile = File(None, description=""),
    visibility: Optional[HubVisibility] = Form(None, description=""),
    summary: Optional[StrictStr] = Form(None, description=""),
    readme: Optional[StrictStr] = Form(None, description=""),
    tags: Optional[List[StrictStr]] = Form(None, description=""),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth
    ),
) -> HubPackageVersionDetail:
    if not BaseHubPackagesApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseHubPackagesApi.subclasses[0]().publish_hub_package(file, visibility, summary, readme, tags)


@router.get(
    "/api/v1/hub/packages/{packageName}",
    responses={
        200: {"model": HubPackageDetail, "description": "OK"},
        404: {"model": Error, "description": "Resource not found"},
    },
    tags=["HubPackages"],
    summary="Get hub package detail",
    response_model_by_alias=True,
)
async def get_hub_package(
    packageName: StrictStr = Path(..., description=""),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth
    ),
) -> HubPackageDetail:
    if not BaseHubPackagesApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseHubPackagesApi.subclasses[0]().get_hub_package(packageName)


@router.get(
    "/api/v1/hub/packages/{packageName}/versions/{version}",
    responses={
        200: {"model": HubPackageVersionDetail, "description": "OK"},
        404: {"model": Error, "description": "Resource not found"},
    },
    tags=["HubPackages"],
    summary="Get hub package version detail",
    response_model_by_alias=True,
)
async def get_hub_package_version(
    packageName: StrictStr = Path(..., description=""),
    version: StrictStr = Path(..., description=""),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth
    ),
) -> HubPackageVersionDetail:
    if not BaseHubPackagesApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseHubPackagesApi.subclasses[0]().get_hub_package_version(packageName, version)


@router.get(
    "/api/v1/hub/packages/{packageName}/archive",
    responses={
        200: {"model": Any, "description": "OK"},
        404: {"model": Error, "description": "Resource not found"},
    },
    tags=["HubPackages"],
    summary="Download hub package archive",
    response_model_by_alias=True,
)
async def download_hub_package_archive(
    packageName: StrictStr = Path(..., description=""),
    version: Annotated[Optional[StrictStr], Field(description="Optional version to download")] = Query(None, description="Optional version to download", alias="version"),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth
    ),
) -> Any:
    if not BaseHubPackagesApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseHubPackagesApi.subclasses[0]().download_hub_package_archive(packageName, version)


@router.post(
    "/api/v1/hub/packages/{packageName}/install",
    responses={
        200: {"model": HubPackageInstallResponse, "description": "OK"},
        404: {"model": Error, "description": "Resource not found"},
    },
    tags=["HubPackages"],
    summary="Install hub package into the local catalog",
    response_model_by_alias=True,
)
async def install_hub_package(
    packageName: StrictStr = Path(..., description=""),
    hub_package_install_request: Optional[HubPackageInstallRequest] = Body(None, description=""),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth
    ),
) -> HubPackageInstallResponse:
    if not BaseHubPackagesApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseHubPackagesApi.subclasses[0]().install_hub_package(packageName, hub_package_install_request)
