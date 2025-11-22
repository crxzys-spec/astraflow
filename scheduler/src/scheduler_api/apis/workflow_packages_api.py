# coding: utf-8

from typing import Dict, List  # noqa: F401
import importlib
import pkgutil

from scheduler_api.apis.workflow_packages_api_base import BaseWorkflowPackagesApi
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
from typing import Any, Optional
from typing_extensions import Annotated
from scheduler_api.models.auth_login401_response import AuthLogin401Response
from scheduler_api.models.clone_workflow_package_request import CloneWorkflowPackageRequest
from scheduler_api.models.get_workflow_package200_response import GetWorkflowPackage200Response
from scheduler_api.models.list_workflow_package_versions200_response import ListWorkflowPackageVersions200Response
from scheduler_api.models.list_workflow_packages200_response import ListWorkflowPackages200Response
from scheduler_api.models.persist_workflow201_response import PersistWorkflow201Response
from scheduler_api.models.publish_workflow200_response import PublishWorkflow200Response
from scheduler_api.models.publish_workflow_request import PublishWorkflowRequest
from scheduler_api.security_api import get_token_bearerAuth

router = APIRouter()

ns_pkg = scheduler_api.impl
for _, name, _ in pkgutil.iter_modules(ns_pkg.__path__, ns_pkg.__name__ + "."):
    importlib.import_module(name)


@router.get(
    "/api/v1/workflow-packages",
    responses={
        200: {"model": ListWorkflowPackages200Response, "description": "OK"},
    },
    tags=["WorkflowPackages"],
    summary="List published workflow packages",
    response_model_by_alias=True,
)
async def list_workflow_packages(
    limit: Optional[Annotated[int, Field(le=200, ge=1)]] = Query(50, description="", alias="limit", ge=1, le=200),
    cursor: Optional[StrictStr] = Query(None, description="", alias="cursor"),
    owner: Annotated[Optional[StrictStr], Field(description="Filter by owner id; use `me` for the caller's id.")] = Query(None, description="Filter by owner id; use &#x60;me&#x60; for the caller&#39;s id.", alias="owner"),
    visibility: Annotated[Optional[StrictStr], Field(description="Filter by visibility (private, internal, public).")] = Query(None, description="Filter by visibility (private, internal, public).", alias="visibility"),
    search: Annotated[Optional[StrictStr], Field(description="Full-text search across slug, display name, and summary.")] = Query(None, description="Full-text search across slug, display name, and summary.", alias="search"),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth
    ),
) -> ListWorkflowPackages200Response:
    if not BaseWorkflowPackagesApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseWorkflowPackagesApi.subclasses[0]().list_workflow_packages(limit, cursor, owner, visibility, search)


@router.get(
    "/api/v1/workflow-packages/{packageId}",
    responses={
        200: {"model": GetWorkflowPackage200Response, "description": "OK"},
        404: {"model": AuthLogin401Response, "description": "Resource not found"},
    },
    tags=["WorkflowPackages"],
    summary="Get a workflow package detail",
    response_model_by_alias=True,
)
async def get_workflow_package(
    packageId: StrictStr = Path(..., description=""),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth
    ),
) -> GetWorkflowPackage200Response:
    if not BaseWorkflowPackagesApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseWorkflowPackagesApi.subclasses[0]().get_workflow_package(packageId)


@router.delete(
    "/api/v1/workflow-packages/{packageId}",
    responses={
        204: {"description": "Deleted"},
        404: {"model": AuthLogin401Response, "description": "Resource not found"},
    },
    tags=["WorkflowPackages"],
    summary="Delete a workflow package",
    response_model_by_alias=True,
)
async def delete_workflow_package(
    packageId: StrictStr = Path(..., description=""),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth
    ),
) -> None:
    if not BaseWorkflowPackagesApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseWorkflowPackagesApi.subclasses[0]().delete_workflow_package(packageId)


@router.get(
    "/api/v1/workflow-packages/{packageId}/versions",
    responses={
        200: {"model": ListWorkflowPackageVersions200Response, "description": "OK"},
        404: {"model": AuthLogin401Response, "description": "Resource not found"},
    },
    tags=["WorkflowPackages"],
    summary="List versions for a workflow package",
    response_model_by_alias=True,
)
async def list_workflow_package_versions(
    packageId: StrictStr = Path(..., description=""),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth
    ),
) -> ListWorkflowPackageVersions200Response:
    if not BaseWorkflowPackagesApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseWorkflowPackagesApi.subclasses[0]().list_workflow_package_versions(packageId)


@router.post(
    "/api/v1/workflow-packages/{packageId}/clone",
    responses={
        201: {"model": PersistWorkflow201Response, "description": "Created"},
        404: {"model": AuthLogin401Response, "description": "Resource not found"},
    },
    tags=["WorkflowPackages"],
    summary="Clone a workflow package version into the caller&#39;s workspace",
    response_model_by_alias=True,
)
async def clone_workflow_package(
    packageId: StrictStr = Path(..., description=""),
    clone_workflow_package_request: Optional[CloneWorkflowPackageRequest] = Body(None, description=""),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth
    ),
) -> PersistWorkflow201Response:
    if not BaseWorkflowPackagesApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseWorkflowPackagesApi.subclasses[0]().clone_workflow_package(packageId, clone_workflow_package_request)


@router.post(
    "/api/v1/workflows/{workflowId}/publish",
    responses={
        200: {"model": PublishWorkflow200Response, "description": "OK"},
        400: {"model": AuthLogin401Response, "description": "Invalid input"},
        403: {"model": AuthLogin401Response, "description": "Authenticated but lacks required permissions"},
        404: {"model": AuthLogin401Response, "description": "Resource not found"},
        409: {"model": AuthLogin401Response, "description": "Conflict (e.g., idempotency-key reuse with different body)"},
    },
    tags=["WorkflowPackages"],
    summary="Publish a workflow draft to the Store",
    response_model_by_alias=True,
)
async def publish_workflow(
    workflowId: StrictStr = Path(..., description=""),
    publish_workflow_request: PublishWorkflowRequest = Body(None, description=""),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth
    ),
) -> PublishWorkflow200Response:
    if not BaseWorkflowPackagesApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseWorkflowPackagesApi.subclasses[0]().publish_workflow(workflowId, publish_workflow_request)
