# coding: utf-8

from typing import Dict, List  # noqa: F401
import importlib
import pkgutil

from hub_api.apis.workflows_api_base import BaseWorkflowsApi
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
)

from hub_api.models.extra_models import TokenModel  # noqa: F401
from pydantic import Field, StrictStr
from typing import Optional
from typing_extensions import Annotated
from hub_api.models.error import Error
from hub_api.models.hub_workflow_detail import HubWorkflowDetail
from hub_api.models.workflow_definition import WorkflowDefinition
from hub_api.models.workflow_list_response import WorkflowListResponse
from hub_api.models.workflow_publish_request import WorkflowPublishRequest
from hub_api.models.workflow_publish_response import WorkflowPublishResponse
from hub_api.models.workflow_version_detail import WorkflowVersionDetail
from hub_api.models.workflow_version_list import WorkflowVersionList
from hub_api.security_api import get_token_bearerAuth

router = APIRouter()

ns_pkg = hub_api.impl
for _, name, _ in pkgutil.iter_modules(ns_pkg.__path__, ns_pkg.__name__ + "."):
    importlib.import_module(name)


@router.get(
    "/api/v1/workflows",
    responses={
        200: {"model": WorkflowListResponse, "description": "OK"},
    },
    tags=["Workflows"],
    summary="List workflows",
    response_model_by_alias=True,
)
async def list_workflows(
    q: Annotated[Optional[StrictStr], Field(description="Search query")] = Query(None, description="Search query", alias="q"),
    tag: Annotated[Optional[StrictStr], Field(description="Filter by tag")] = Query(None, description="Filter by tag", alias="tag"),
    owner: Annotated[Optional[StrictStr], Field(description="Filter by owner id")] = Query(None, description="Filter by owner id", alias="owner"),
    page: Annotated[Optional[Annotated[int, Field(ge=1)]], Field(description="1-based page index")] = Query(1, description="1-based page index", alias="page", ge=1),
    page_size: Annotated[Optional[Annotated[int, Field(le=200, ge=1)]], Field(description="Page size")] = Query(20, description="Page size", alias="pageSize", ge=1, le=200),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth, scopes=[]
    ),
) -> WorkflowListResponse:
    if not BaseWorkflowsApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseWorkflowsApi.subclasses[0]().list_workflows(q, tag, owner, page, page_size)


@router.post(
    "/api/v1/workflows",
    responses={
        201: {"model": WorkflowPublishResponse, "description": "Created"},
        400: {"model": Error, "description": "Invalid input"},
        401: {"model": Error, "description": "Unauthorized"},
        403: {"model": Error, "description": "Forbidden"},
        409: {"model": Error, "description": "Conflict"},
    },
    tags=["Workflows"],
    summary="Publish workflow",
    response_model_by_alias=True,
)
async def publish_workflow(
    workflow_publish_request: WorkflowPublishRequest = Body(None, description=""),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth, scopes=["publish"]
    ),
) -> WorkflowPublishResponse:
    if not BaseWorkflowsApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseWorkflowsApi.subclasses[0]().publish_workflow(workflow_publish_request)


@router.get(
    "/api/v1/workflows/{workflowId}",
    responses={
        200: {"model": HubWorkflowDetail, "description": "OK"},
        404: {"model": Error, "description": "Not Found"},
    },
    tags=["Workflows"],
    summary="Get workflow detail",
    response_model_by_alias=True,
)
async def get_workflow(
    workflowId: StrictStr = Path(..., description=""),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth, scopes=[]
    ),
) -> HubWorkflowDetail:
    if not BaseWorkflowsApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseWorkflowsApi.subclasses[0]().get_workflow(workflowId)


@router.get(
    "/api/v1/workflows/{workflowId}/versions",
    responses={
        200: {"model": WorkflowVersionList, "description": "OK"},
        404: {"model": Error, "description": "Not Found"},
    },
    tags=["Workflows"],
    summary="List workflow versions",
    response_model_by_alias=True,
)
async def list_workflow_versions(
    workflowId: StrictStr = Path(..., description=""),
    page: Annotated[Optional[Annotated[int, Field(ge=1)]], Field(description="1-based page index")] = Query(1, description="1-based page index", alias="page", ge=1),
    page_size: Annotated[Optional[Annotated[int, Field(le=200, ge=1)]], Field(description="Page size")] = Query(20, description="Page size", alias="pageSize", ge=1, le=200),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth, scopes=[]
    ),
) -> WorkflowVersionList:
    if not BaseWorkflowsApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseWorkflowsApi.subclasses[0]().list_workflow_versions(workflowId, page, page_size)


@router.get(
    "/api/v1/workflows/{workflowId}/versions/{versionId}",
    responses={
        200: {"model": WorkflowVersionDetail, "description": "OK"},
        404: {"model": Error, "description": "Not Found"},
    },
    tags=["Workflows"],
    summary="Get workflow version detail",
    response_model_by_alias=True,
)
async def get_workflow_version(
    workflowId: StrictStr = Path(..., description=""),
    versionId: StrictStr = Path(..., description=""),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth, scopes=[]
    ),
) -> WorkflowVersionDetail:
    if not BaseWorkflowsApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseWorkflowsApi.subclasses[0]().get_workflow_version(workflowId, versionId)


@router.get(
    "/api/v1/workflows/{workflowId}/versions/{versionId}/definition",
    responses={
        200: {"model": WorkflowDefinition, "description": "OK"},
        404: {"model": Error, "description": "Not Found"},
    },
    tags=["Workflows"],
    summary="Get workflow definition snapshot",
    response_model_by_alias=True,
)
async def get_workflow_definition(
    workflowId: StrictStr = Path(..., description=""),
    versionId: StrictStr = Path(..., description=""),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth, scopes=[]
    ),
) -> WorkflowDefinition:
    if not BaseWorkflowsApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseWorkflowsApi.subclasses[0]().get_workflow_definition(workflowId, versionId)
