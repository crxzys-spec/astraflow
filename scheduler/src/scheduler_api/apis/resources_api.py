# coding: utf-8

from typing import Dict, List  # noqa: F401
import importlib
import pkgutil

from scheduler_api.apis.resources_api_base import BaseResourcesApi
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
from scheduler_api.models.resource import Resource
from scheduler_api.models.resource_grant import ResourceGrant
from scheduler_api.models.resource_grant_create_request import ResourceGrantCreateRequest
from scheduler_api.models.resource_grant_list import ResourceGrantList
from scheduler_api.models.resource_grant_scope import ResourceGrantScope
from scheduler_api.models.resource_list import ResourceList
from scheduler_api.models.resource_upload_init_request import ResourceUploadInitRequest
from scheduler_api.models.resource_upload_part import ResourceUploadPart
from scheduler_api.models.resource_upload_session import ResourceUploadSession
from scheduler_api.security_api import get_token_bearerAuth

router = APIRouter()

ns_pkg = scheduler_api.impl
for _, name, _ in pkgutil.iter_modules(ns_pkg.__path__, ns_pkg.__name__ + "."):
    importlib.import_module(name)


@router.get(
    "/api/v1/resources",
    responses={
        200: {"model": ResourceList, "description": "OK"},
    },
    tags=["Resources"],
    summary="List resources",
    response_model_by_alias=True,
)
async def list_resources(
    limit: Optional[Annotated[int, Field(le=200, ge=1)]] = Query(50, description="", alias="limit", ge=1, le=200),
    cursor: Optional[StrictStr] = Query(None, description="", alias="cursor"),
    search: Optional[StrictStr] = Query(None, description="", alias="search"),
    owner_id: Optional[StrictStr] = Query(None, description="", alias="ownerId"),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth
    ),
) -> ResourceList:
    if not BaseResourcesApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseResourcesApi.subclasses[0]().list_resources(limit, cursor, search, owner_id)


@router.post(
    "/api/v1/resources",
    responses={
        201: {"model": Resource, "description": "Created"},
        400: {"model": Error, "description": "Invalid input"},
    },
    tags=["Resources"],
    summary="Upload resource",
    response_model_by_alias=True,
)
async def upload_resource(
    file: UploadFile = File(None, description=""),
    provider: Optional[StrictStr] = Form(None, description=""),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth
    ),
) -> Resource:
    if not BaseResourcesApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseResourcesApi.subclasses[0]().upload_resource(file, provider)


@router.post(
    "/api/v1/resources/uploads",
    responses={
        201: {"model": ResourceUploadSession, "description": "Created"},
        400: {"model": Error, "description": "Invalid input"},
    },
    tags=["Resources"],
    summary="Create resource upload session",
    response_model_by_alias=True,
)
async def create_resource_upload(
    resource_upload_init_request: ResourceUploadInitRequest = Body(None, description=""),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth
    ),
) -> ResourceUploadSession:
    if not BaseResourcesApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseResourcesApi.subclasses[0]().create_resource_upload(resource_upload_init_request)


@router.get(
    "/api/v1/resources/uploads/{uploadId}",
    responses={
        200: {"model": ResourceUploadSession, "description": "OK"},
        404: {"model": Error, "description": "Resource not found"},
    },
    tags=["Resources"],
    summary="Get resource upload session",
    response_model_by_alias=True,
)
async def get_resource_upload(
    uploadId: StrictStr = Path(..., description=""),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth
    ),
) -> ResourceUploadSession:
    if not BaseResourcesApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseResourcesApi.subclasses[0]().get_resource_upload(uploadId)


@router.delete(
    "/api/v1/resources/uploads/{uploadId}",
    responses={
        204: {"description": "Deleted"},
        404: {"model": Error, "description": "Resource not found"},
    },
    tags=["Resources"],
    summary="Abort resource upload session",
    response_model_by_alias=True,
)
async def delete_resource_upload(
    uploadId: StrictStr = Path(..., description=""),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth
    ),
) -> None:
    if not BaseResourcesApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseResourcesApi.subclasses[0]().delete_resource_upload(uploadId)


@router.put(
    "/api/v1/resources/uploads/{uploadId}/parts/{partNumber}",
    responses={
        200: {"model": ResourceUploadPart, "description": "OK"},
        400: {"model": Error, "description": "Invalid input"},
        404: {"model": Error, "description": "Resource not found"},
        409: {"model": Error, "description": "Conflict (e.g., idempotency-key reuse with different body)"},
    },
    tags=["Resources"],
    summary="Upload resource part",
    response_model_by_alias=True,
)
async def upload_resource_part(
    uploadId: StrictStr = Path(..., description=""),
    partNumber: Annotated[int, Field(ge=0)] = Path(..., description="", ge=0),
    file: UploadFile = File(None, description=""),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth
    ),
) -> ResourceUploadPart:
    if not BaseResourcesApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseResourcesApi.subclasses[0]().upload_resource_part(uploadId, partNumber, file)


@router.post(
    "/api/v1/resources/uploads/{uploadId}/complete",
    responses={
        201: {"model": Resource, "description": "Created"},
        400: {"model": Error, "description": "Invalid input"},
        404: {"model": Error, "description": "Resource not found"},
    },
    tags=["Resources"],
    summary="Complete resource upload",
    response_model_by_alias=True,
)
async def complete_resource_upload(
    uploadId: StrictStr = Path(..., description=""),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth
    ),
) -> Resource:
    if not BaseResourcesApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseResourcesApi.subclasses[0]().complete_resource_upload(uploadId)


@router.get(
    "/api/v1/resources/{resourceId}",
    responses={
        200: {"model": Resource, "description": "OK"},
        404: {"model": Error, "description": "Resource not found"},
    },
    tags=["Resources"],
    summary="Get resource metadata",
    response_model_by_alias=True,
)
async def get_resource(
    resourceId: StrictStr = Path(..., description=""),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth
    ),
) -> Resource:
    if not BaseResourcesApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseResourcesApi.subclasses[0]().get_resource(resourceId)


@router.delete(
    "/api/v1/resources/{resourceId}",
    responses={
        204: {"description": "Deleted"},
        404: {"model": Error, "description": "Resource not found"},
    },
    tags=["Resources"],
    summary="Delete resource",
    response_model_by_alias=True,
)
async def delete_resource(
    resourceId: StrictStr = Path(..., description=""),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth
    ),
) -> None:
    if not BaseResourcesApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseResourcesApi.subclasses[0]().delete_resource(resourceId)


@router.get(
    "/api/v1/resources/{resourceId}/download",
    responses={
        200: {"model": Any, "description": "OK"},
        404: {"model": Error, "description": "Resource not found"},
    },
    tags=["Resources"],
    summary="Download resource",
    response_model_by_alias=True,
)
async def download_resource(
    resourceId: StrictStr = Path(..., description=""),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth
    ),
) -> Any:
    if not BaseResourcesApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseResourcesApi.subclasses[0]().download_resource(resourceId)


@router.get(
    "/api/v1/resource-grants",
    responses={
        200: {"model": ResourceGrantList, "description": "OK"},
    },
    tags=["Resources"],
    summary="List resource grants",
    response_model_by_alias=True,
)
async def list_resource_grants(
    workflow_id: Optional[StrictStr] = Query(None, description="", alias="workflowId"),
    package_name: Optional[StrictStr] = Query(None, description="", alias="packageName"),
    package_version: Optional[StrictStr] = Query(None, description="", alias="packageVersion"),
    resource_key: Optional[StrictStr] = Query(None, description="", alias="resourceKey"),
    scope: Optional[ResourceGrantScope] = Query(None, description="", alias="scope"),
    resource_id: Optional[StrictStr] = Query(None, description="", alias="resourceId"),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth
    ),
) -> ResourceGrantList:
    if not BaseResourcesApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseResourcesApi.subclasses[0]().list_resource_grants(workflow_id, package_name, package_version, resource_key, scope, resource_id)


@router.post(
    "/api/v1/resource-grants",
    responses={
        201: {"model": ResourceGrant, "description": "Created"},
        400: {"model": Error, "description": "Invalid input"},
    },
    tags=["Resources"],
    summary="Create resource grant",
    response_model_by_alias=True,
)
async def create_resource_grant(
    resource_grant_create_request: ResourceGrantCreateRequest = Body(None, description=""),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth
    ),
) -> ResourceGrant:
    if not BaseResourcesApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseResourcesApi.subclasses[0]().create_resource_grant(resource_grant_create_request)


@router.get(
    "/api/v1/resource-grants/{grantId}",
    responses={
        200: {"model": ResourceGrant, "description": "OK"},
        404: {"model": Error, "description": "Resource not found"},
    },
    tags=["Resources"],
    summary="Get resource grant",
    response_model_by_alias=True,
)
async def get_resource_grant(
    grantId: StrictStr = Path(..., description=""),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth
    ),
) -> ResourceGrant:
    if not BaseResourcesApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseResourcesApi.subclasses[0]().get_resource_grant(grantId)


@router.delete(
    "/api/v1/resource-grants/{grantId}",
    responses={
        204: {"description": "Deleted"},
        404: {"model": Error, "description": "Resource not found"},
    },
    tags=["Resources"],
    summary="Delete resource grant",
    response_model_by_alias=True,
)
async def delete_resource_grant(
    grantId: StrictStr = Path(..., description=""),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth
    ),
) -> None:
    if not BaseResourcesApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseResourcesApi.subclasses[0]().delete_resource_grant(grantId)
