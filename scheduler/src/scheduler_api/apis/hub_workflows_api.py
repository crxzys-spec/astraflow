# coding: utf-8

from typing import Dict, List, Any  # noqa: F401
import importlib
import pkgutil

from scheduler_api.apis.hub_workflows_api_base import BaseHubWorkflowsApi
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
from typing import Any, Dict, Optional
from typing_extensions import Annotated
from scheduler_api.models.error import Error
from scheduler_api.models.hub_workflow_detail import HubWorkflowDetail
from scheduler_api.models.hub_workflow_import_request import HubWorkflowImportRequest
from scheduler_api.models.hub_workflow_import_response import HubWorkflowImportResponse
from scheduler_api.models.hub_workflow_list_response import HubWorkflowListResponse
from scheduler_api.models.hub_workflow_publish_request import HubWorkflowPublishRequest
from scheduler_api.models.hub_workflow_publish_response import HubWorkflowPublishResponse
from scheduler_api.models.hub_workflow_version_detail import HubWorkflowVersionDetail
from scheduler_api.models.hub_workflow_version_list import HubWorkflowVersionList
from scheduler_api.security_api import get_token_bearerAuth

router = APIRouter()

ns_pkg = scheduler_api.impl
for _, name, _ in pkgutil.iter_modules(ns_pkg.__path__, ns_pkg.__name__ + "."):
    importlib.import_module(name)


@router.get(
    "/api/v1/hub/workflows",
    responses={
        200: {"model": HubWorkflowListResponse, "description": "OK"},
    },
    tags=["HubWorkflows"],
    summary="List hub workflows",
    response_model_by_alias=True,
)
async def list_hub_workflows(
    q: Annotated[Optional[StrictStr], Field(description="Search query")] = Query(None, description="Search query", alias="q"),
    tag: Annotated[Optional[StrictStr], Field(description="Filter by tag")] = Query(None, description="Filter by tag", alias="tag"),
    owner: Annotated[Optional[StrictStr], Field(description="Filter by owner id")] = Query(None, description="Filter by owner id", alias="owner"),
    page: Annotated[Optional[Annotated[int, Field(ge=1)]], Field(description="1-based page index")] = Query(1, description="1-based page index", alias="page", ge=1),
    page_size: Annotated[Optional[Annotated[int, Field(le=200, ge=1)]], Field(description="Page size")] = Query(20, description="Page size", alias="pageSize", ge=1, le=200),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth
    ),
) -> HubWorkflowListResponse:
    if not BaseHubWorkflowsApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseHubWorkflowsApi.subclasses[0]().list_hub_workflows(q, tag, owner, page, page_size)


@router.post(
    "/api/v1/hub/workflows",
    responses={
        201: {"model": HubWorkflowPublishResponse, "description": "Created"},
        400: {"model": Error, "description": "Invalid input"},
        401: {"model": Error, "description": "Authentication required or credentials invalid"},
        403: {"model": Error, "description": "Authenticated but lacks required permissions"},
    },
    tags=["HubWorkflows"],
    summary="Publish a workflow to Hub",
    response_model_by_alias=True,
)
async def publish_hub_workflow(
    hub_workflow_publish_request: HubWorkflowPublishRequest = Body(None, description=""),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth
    ),
) -> HubWorkflowPublishResponse:
    if not BaseHubWorkflowsApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseHubWorkflowsApi.subclasses[0]().publish_hub_workflow(hub_workflow_publish_request)


@router.get(
    "/api/v1/hub/workflows/{workflowId}",
    responses={
        200: {"model": HubWorkflowDetail, "description": "OK"},
        404: {"model": Error, "description": "Resource not found"},
    },
    tags=["HubWorkflows"],
    summary="Get hub workflow detail",
    response_model_by_alias=True,
)
async def get_hub_workflow(
    workflowId: StrictStr = Path(..., description=""),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth
    ),
) -> HubWorkflowDetail:
    if not BaseHubWorkflowsApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseHubWorkflowsApi.subclasses[0]().get_hub_workflow(workflowId)


@router.get(
    "/api/v1/hub/workflows/{workflowId}/versions",
    responses={
        200: {"model": HubWorkflowVersionList, "description": "OK"},
        404: {"model": Error, "description": "Resource not found"},
    },
    tags=["HubWorkflows"],
    summary="List hub workflow versions",
    response_model_by_alias=True,
)
async def list_hub_workflow_versions(
    workflowId: StrictStr = Path(..., description=""),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth
    ),
) -> HubWorkflowVersionList:
    if not BaseHubWorkflowsApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseHubWorkflowsApi.subclasses[0]().list_hub_workflow_versions(workflowId)


@router.get(
    "/api/v1/hub/workflows/{workflowId}/versions/{versionId}",
    responses={
        200: {"model": HubWorkflowVersionDetail, "description": "OK"},
        404: {"model": Error, "description": "Resource not found"},
    },
    tags=["HubWorkflows"],
    summary="Get hub workflow version detail",
    response_model_by_alias=True,
)
async def get_hub_workflow_version(
    workflowId: StrictStr = Path(..., description=""),
    versionId: StrictStr = Path(..., description=""),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth
    ),
) -> HubWorkflowVersionDetail:
    if not BaseHubWorkflowsApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseHubWorkflowsApi.subclasses[0]().get_hub_workflow_version(workflowId, versionId)


@router.get(
    "/api/v1/hub/workflows/{workflowId}/versions/{versionId}/definition",
    responses={
        200: {"model": Dict[str, object], "description": "OK"},
        404: {"model": Error, "description": "Resource not found"},
    },
    tags=["HubWorkflows"],
    summary="Get hub workflow definition",
    response_model_by_alias=True,
)
async def get_hub_workflow_definition(
    workflowId: StrictStr = Path(..., description=""),
    versionId: StrictStr = Path(..., description=""),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth
    ),
) -> Dict[str, object]:
    if not BaseHubWorkflowsApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseHubWorkflowsApi.subclasses[0]().get_hub_workflow_definition(workflowId, versionId)


@router.post(
    "/api/v1/hub/workflows/{workflowId}/import",
    responses={
        200: {"model": HubWorkflowImportResponse, "description": "OK"},
        404: {"model": Error, "description": "Resource not found"},
    },
    tags=["HubWorkflows"],
    summary="Import a hub workflow into the local workspace",
    response_model_by_alias=True,
)
async def import_hub_workflow(
    workflowId: StrictStr = Path(..., description=""),
    hub_workflow_import_request: Optional[HubWorkflowImportRequest] = Body(None, description=""),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth
    ),
) -> HubWorkflowImportResponse:
    if not BaseHubWorkflowsApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseHubWorkflowsApi.subclasses[0]().import_hub_workflow(workflowId, hub_workflow_import_request)
