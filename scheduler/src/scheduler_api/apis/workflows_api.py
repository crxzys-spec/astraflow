# coding: utf-8

from typing import Dict, List  # noqa: F401
import importlib
import pkgutil

from scheduler_api.apis.workflows_api_base import BaseWorkflowsApi
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
from scheduler_api.models.error import Error
from scheduler_api.models.workflow import Workflow
from scheduler_api.models.workflow_list import WorkflowList
from scheduler_api.models.workflow_preview import WorkflowPreview
from scheduler_api.models.workflow_ref import WorkflowRef
from scheduler_api.security_api import get_token_bearerAuth

router = APIRouter()

ns_pkg = scheduler_api.impl
for _, name, _ in pkgutil.iter_modules(ns_pkg.__path__, ns_pkg.__name__ + "."):
    importlib.import_module(name)


@router.get(
    "/api/v1/workflows",
    responses={
        200: {"model": WorkflowList, "description": "OK"},
    },
    tags=["Workflows"],
    summary="List stored workflows (paginated)",
    response_model_by_alias=True,
)
async def list_workflows(
    limit: Optional[Annotated[int, Field(le=200, ge=1)]] = Query(50, description="", alias="limit", ge=1, le=200),
    cursor: Optional[StrictStr] = Query(None, description="", alias="cursor"),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth
    ),
) -> WorkflowList:
    if not BaseWorkflowsApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseWorkflowsApi.subclasses[0]().list_workflows(limit, cursor)


@router.post(
    "/api/v1/workflows",
    responses={
        201: {"model": WorkflowRef, "description": "Created"},
        400: {"model": Error, "description": "Invalid input"},
        409: {"model": Error, "description": "Conflict (e.g., idempotency-key reuse with different body)"},
    },
    tags=["Workflows"],
    summary="Persist a workflow for editor storage (no versioning)",
    response_model_by_alias=True,
)
async def persist_workflow(
    workflow: Workflow = Body(None, description=""),
    idempotency_key: Annotated[Optional[Annotated[str, Field(max_length=64)]], Field(description="Optional idempotency key for safe retries; if reused with a different body, return 409")] = Header(None, description="Optional idempotency key for safe retries; if reused with a different body, return 409", max_length=64),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth
    ),
) -> WorkflowRef:
    if not BaseWorkflowsApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseWorkflowsApi.subclasses[0]().persist_workflow(workflow, idempotency_key)


@router.get(
    "/api/v1/workflows/{workflowId}",
    responses={
        200: {"model": Workflow, "description": "OK"},
        404: {"model": Error, "description": "Resource not found"},
    },
    tags=["Workflows"],
    summary="Read stored workflow (latest)",
    response_model_by_alias=True,
)
async def get_workflow(
    workflowId: StrictStr = Path(..., description=""),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth
    ),
) -> Workflow:
    if not BaseWorkflowsApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseWorkflowsApi.subclasses[0]().get_workflow(workflowId)


@router.delete(
    "/api/v1/workflows/{workflowId}",
    responses={
        204: {"description": "Workflow deleted"},
        403: {"model": Error, "description": "Authenticated but lacks required permissions"},
        404: {"model": Error, "description": "Resource not found"},
    },
    tags=["Workflows"],
    summary="Soft delete workflow",
    response_model_by_alias=True,
)
async def delete_workflow(
    workflowId: StrictStr = Path(..., description=""),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth
    ),
) -> None:
    """Marks the workflow record as deleted so it is hidden from listings and future reads."""
    if not BaseWorkflowsApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseWorkflowsApi.subclasses[0]().delete_workflow(workflowId)


@router.get(
    "/api/v1/workflows/{workflowId}/preview",
    responses={
        200: {"model": WorkflowPreview, "description": "OK"},
        404: {"model": Error, "description": "Resource not found"},
    },
    tags=["Workflows"],
    summary="Get workflow canvas preview",
    response_model_by_alias=True,
)
async def get_workflow_preview(
    workflowId: StrictStr = Path(..., description=""),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth
    ),
) -> WorkflowPreview:
    if not BaseWorkflowsApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseWorkflowsApi.subclasses[0]().get_workflow_preview(workflowId)


@router.put(
    "/api/v1/workflows/{workflowId}/preview",
    responses={
        200: {"model": WorkflowPreview, "description": "Updated"},
        404: {"model": Error, "description": "Resource not found"},
    },
    tags=["Workflows"],
    summary="Set or clear workflow canvas preview",
    response_model_by_alias=True,
)
async def set_workflow_preview(
    workflowId: StrictStr = Path(..., description=""),
    workflow_preview: WorkflowPreview = Body(None, description=""),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth
    ),
) -> WorkflowPreview:
    if not BaseWorkflowsApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseWorkflowsApi.subclasses[0]().set_workflow_preview(workflowId, workflow_preview)
