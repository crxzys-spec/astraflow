# coding: utf-8

from typing import Dict, List, Any  # noqa: F401
import importlib
import pkgutil

from hub_api.apis.packages_api_base import BasePackagesApi
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
    File,
    UploadFile,
)

from hub_api.models.extra_models import TokenModel  # noqa: F401
from pydantic import Field, StrictBytes, StrictStr
from typing import Any, List, Optional, Tuple, Union
from typing_extensions import Annotated
from hub_api.models.error import Error
from hub_api.models.hub_package_detail import HubPackageDetail
from hub_api.models.package_list_response import PackageListResponse
from hub_api.models.package_permission import PackagePermission
from hub_api.models.package_permission_create_request import PackagePermissionCreateRequest
from hub_api.models.package_permission_list import PackagePermissionList
from hub_api.models.package_permission_update_request import PackagePermissionUpdateRequest
from hub_api.models.package_registry import PackageRegistry
from hub_api.models.package_reserve_request import PackageReserveRequest
from hub_api.models.package_tag_request import PackageTagRequest
from hub_api.models.package_transfer_request import PackageTransferRequest
from hub_api.models.package_version_detail import PackageVersionDetail
from hub_api.models.package_visibility_request import PackageVisibilityRequest
from hub_api.models.visibility import Visibility
from hub_api.security_api import get_token_bearerAuth

router = APIRouter()

ns_pkg = hub_api.impl
for _, name, _ in pkgutil.iter_modules(ns_pkg.__path__, ns_pkg.__name__ + "."):
    importlib.import_module(name)


@router.get(
    "/api/v1/packages",
    responses={
        200: {"model": PackageListResponse, "description": "OK"},
    },
    tags=["Packages"],
    summary="List packages",
    response_model_by_alias=True,
)
async def list_packages(
    q: Annotated[Optional[StrictStr], Field(description="Search query")] = Query(None, description="Search query", alias="q"),
    tag: Annotated[Optional[StrictStr], Field(description="Filter by tag")] = Query(None, description="Filter by tag", alias="tag"),
    owner: Annotated[Optional[StrictStr], Field(description="Filter by owner id")] = Query(None, description="Filter by owner id", alias="owner"),
    page: Annotated[Optional[Annotated[int, Field(ge=1)]], Field(description="1-based page index")] = Query(1, description="1-based page index", alias="page", ge=1),
    page_size: Annotated[Optional[Annotated[int, Field(le=200, ge=1)]], Field(description="Page size")] = Query(20, description="Page size", alias="pageSize", ge=1, le=200),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth, scopes=[]
    ),
) -> PackageListResponse:
    if not BasePackagesApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BasePackagesApi.subclasses[0]().list_packages(q, tag, owner, page, page_size)


@router.post(
    "/api/v1/packages",
    responses={
        201: {"model": PackageVersionDetail, "description": "Created"},
        400: {"model": Error, "description": "Invalid input"},
        401: {"model": Error, "description": "Unauthorized"},
        403: {"model": Error, "description": "Forbidden"},
        409: {"model": Error, "description": "Conflict"},
    },
    tags=["Packages"],
    summary="Publish a package archive",
    response_model_by_alias=True,
)
async def publish_package(
    file: UploadFile = File(None, description=""),
    visibility: Optional[Visibility] = Form(None, description=""),
    summary: Optional[StrictStr] = Form(None, description=""),
    readme: Optional[StrictStr] = Form(None, description=""),
    tags: Optional[List[StrictStr]] = Form(None, description=""),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth, scopes=["publish"]
    ),
) -> PackageVersionDetail:
    if not BasePackagesApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BasePackagesApi.subclasses[0]().publish_package(file, visibility, summary, readme, tags)


@router.get(
    "/api/v1/packages/{name}",
    responses={
        200: {"model": HubPackageDetail, "description": "OK"},
        404: {"model": Error, "description": "Not Found"},
    },
    tags=["Packages"],
    summary="Get package detail",
    response_model_by_alias=True,
)
async def get_package(
    name: StrictStr = Path(..., description=""),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth, scopes=[]
    ),
) -> HubPackageDetail:
    if not BasePackagesApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BasePackagesApi.subclasses[0]().get_package(name)


@router.post(
    "/api/v1/packages/{name}/reserve",
    responses={
        200: {"model": PackageRegistry, "description": "OK"},
        400: {"model": Error, "description": "Invalid input"},
        401: {"model": Error, "description": "Unauthorized"},
        403: {"model": Error, "description": "Forbidden"},
        409: {"model": Error, "description": "Conflict"},
    },
    tags=["Packages"],
    summary="Reserve package name",
    response_model_by_alias=True,
)
async def reserve_package(
    name: StrictStr = Path(..., description=""),
    package_reserve_request: Optional[PackageReserveRequest] = Body(None, description=""),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth, scopes=["publish"]
    ),
) -> PackageRegistry:
    if not BasePackagesApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BasePackagesApi.subclasses[0]().reserve_package(name, package_reserve_request)


@router.get(
    "/api/v1/packages/{name}/versions/{version}",
    responses={
        200: {"model": PackageVersionDetail, "description": "OK"},
        404: {"model": Error, "description": "Not Found"},
    },
    tags=["Packages"],
    summary="Get package version detail",
    response_model_by_alias=True,
)
async def get_package_version(
    name: StrictStr = Path(..., description=""),
    version: StrictStr = Path(..., description=""),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth, scopes=[]
    ),
) -> PackageVersionDetail:
    if not BasePackagesApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BasePackagesApi.subclasses[0]().get_package_version(name, version)


@router.get(
    "/api/v1/packages/{name}/archive",
    responses={
        200: {"model": Any, "description": "OK"},
        404: {"model": Error, "description": "Not Found"},
    },
    tags=["Packages"],
    summary="Download package archive",
    response_model_by_alias=True,
)
async def download_package_archive(
    name: StrictStr = Path(..., description=""),
    version: Annotated[Optional[StrictStr], Field(description="Optional version to download")] = Query(None, description="Optional version to download", alias="version"),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth, scopes=[]
    ),
) -> Any:
    if not BasePackagesApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BasePackagesApi.subclasses[0]().download_package_archive(name, version)


@router.put(
    "/api/v1/packages/{name}/tags/{tag}",
    responses={
        204: {"description": "Updated"},
        400: {"model": Error, "description": "Invalid input"},
        401: {"model": Error, "description": "Unauthorized"},
        403: {"model": Error, "description": "Forbidden"},
        404: {"model": Error, "description": "Not Found"},
    },
    tags=["Packages"],
    summary="Set package dist-tag",
    response_model_by_alias=True,
)
async def set_package_tag(
    name: StrictStr = Path(..., description=""),
    tag: StrictStr = Path(..., description=""),
    package_tag_request: PackageTagRequest = Body(None, description=""),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth, scopes=["publish"]
    ),
) -> None:
    if not BasePackagesApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BasePackagesApi.subclasses[0]().set_package_tag(name, tag, package_tag_request)


@router.delete(
    "/api/v1/packages/{name}/tags/{tag}",
    responses={
        204: {"description": "Deleted"},
        401: {"model": Error, "description": "Unauthorized"},
        403: {"model": Error, "description": "Forbidden"},
        404: {"model": Error, "description": "Not Found"},
    },
    tags=["Packages"],
    summary="Delete package dist-tag",
    response_model_by_alias=True,
)
async def delete_package_tag(
    name: StrictStr = Path(..., description=""),
    tag: StrictStr = Path(..., description=""),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth, scopes=["publish"]
    ),
) -> None:
    if not BasePackagesApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BasePackagesApi.subclasses[0]().delete_package_tag(name, tag)


@router.patch(
    "/api/v1/packages/{name}/visibility",
    responses={
        200: {"model": PackageRegistry, "description": "OK"},
        400: {"model": Error, "description": "Invalid input"},
        401: {"model": Error, "description": "Unauthorized"},
        403: {"model": Error, "description": "Forbidden"},
        404: {"model": Error, "description": "Not Found"},
    },
    tags=["Packages"],
    summary="Update package visibility",
    response_model_by_alias=True,
)
async def update_package_visibility(
    name: StrictStr = Path(..., description=""),
    package_visibility_request: PackageVisibilityRequest = Body(None, description=""),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth, scopes=["publish"]
    ),
) -> PackageRegistry:
    if not BasePackagesApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BasePackagesApi.subclasses[0]().update_package_visibility(name, package_visibility_request)


@router.post(
    "/api/v1/packages/{name}/transfer",
    responses={
        200: {"model": PackageRegistry, "description": "OK"},
        400: {"model": Error, "description": "Invalid input"},
        401: {"model": Error, "description": "Unauthorized"},
        403: {"model": Error, "description": "Forbidden"},
        404: {"model": Error, "description": "Not Found"},
    },
    tags=["Packages"],
    summary="Transfer package ownership",
    response_model_by_alias=True,
)
async def transfer_package(
    name: StrictStr = Path(..., description=""),
    package_transfer_request: PackageTransferRequest = Body(None, description=""),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth, scopes=["publish"]
    ),
) -> PackageRegistry:
    if not BasePackagesApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BasePackagesApi.subclasses[0]().transfer_package(name, package_transfer_request)


@router.get(
    "/api/v1/packages/{name}/permissions",
    responses={
        200: {"model": PackagePermissionList, "description": "OK"},
        401: {"model": Error, "description": "Unauthorized"},
        403: {"model": Error, "description": "Forbidden"},
        404: {"model": Error, "description": "Not Found"},
    },
    tags=["Packages"],
    summary="List package permissions",
    response_model_by_alias=True,
)
async def list_package_permissions(
    name: StrictStr = Path(..., description=""),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth, scopes=["publish"]
    ),
) -> PackagePermissionList:
    if not BasePackagesApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BasePackagesApi.subclasses[0]().list_package_permissions(name)


@router.post(
    "/api/v1/packages/{name}/permissions",
    responses={
        201: {"model": PackagePermission, "description": "Created"},
        400: {"model": Error, "description": "Invalid input"},
        401: {"model": Error, "description": "Unauthorized"},
        403: {"model": Error, "description": "Forbidden"},
    },
    tags=["Packages"],
    summary="Add package permission",
    response_model_by_alias=True,
)
async def add_package_permission(
    name: StrictStr = Path(..., description=""),
    package_permission_create_request: PackagePermissionCreateRequest = Body(None, description=""),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth, scopes=["publish"]
    ),
) -> PackagePermission:
    if not BasePackagesApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BasePackagesApi.subclasses[0]().add_package_permission(name, package_permission_create_request)


@router.delete(
    "/api/v1/packages/{name}/permissions/{permissionId}",
    responses={
        204: {"description": "Deleted"},
        401: {"model": Error, "description": "Unauthorized"},
        403: {"model": Error, "description": "Forbidden"},
        404: {"model": Error, "description": "Not Found"},
    },
    tags=["Packages"],
    summary="Remove package permission",
    response_model_by_alias=True,
)
async def delete_package_permission(
    name: StrictStr = Path(..., description=""),
    permissionId: StrictStr = Path(..., description=""),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth, scopes=["publish"]
    ),
) -> None:
    if not BasePackagesApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BasePackagesApi.subclasses[0]().delete_package_permission(name, permissionId)


@router.patch(
    "/api/v1/packages/{name}/permissions/{permissionId}",
    responses={
        200: {"model": PackagePermission, "description": "OK"},
        400: {"model": Error, "description": "Invalid input"},
        401: {"model": Error, "description": "Unauthorized"},
        403: {"model": Error, "description": "Forbidden"},
        404: {"model": Error, "description": "Not Found"},
    },
    tags=["Packages"],
    summary="Update package permission",
    response_model_by_alias=True,
)
async def update_package_permission(
    name: StrictStr = Path(..., description=""),
    permissionId: StrictStr = Path(..., description=""),
    package_permission_update_request: PackagePermissionUpdateRequest = Body(None, description=""),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth, scopes=["publish"]
    ),
) -> PackagePermission:
    if not BasePackagesApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BasePackagesApi.subclasses[0]().update_package_permission(name, permissionId, package_permission_update_request)
