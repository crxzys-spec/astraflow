# coding: utf-8

from typing import Dict, List  # noqa: F401
import importlib
import pkgutil

from scheduler_api.apis.runs_api_base import BaseRunsApi
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
from scheduler_api.models.run import Run
from scheduler_api.models.run_list import RunList
from scheduler_api.models.run_ref import RunRef
from scheduler_api.models.run_start_request import RunStartRequest
from scheduler_api.models.run_status import RunStatus
from scheduler_api.models.workflow import Workflow
from scheduler_api.security_api import get_token_bearerAuth

router = APIRouter()

ns_pkg = scheduler_api.impl
for _, name, _ in pkgutil.iter_modules(ns_pkg.__path__, ns_pkg.__name__ + "."):
    importlib.import_module(name)


@router.get(
    "/api/v1/runs",
    responses={
        200: {"model": RunList, "description": "OK"},
    },
    tags=["Runs"],
    summary="List runs (paginated)",
    response_model_by_alias=True,
)
async def list_runs(
    limit: Optional[Annotated[int, Field(le=200, ge=1)]] = Query(50, description="", alias="limit", ge=1, le=200),
    cursor: Optional[StrictStr] = Query(None, description="", alias="cursor"),
    status: Optional[RunStatus] = Query(None, description="", alias="status"),
    client_id: Optional[StrictStr] = Query(None, description="", alias="clientId"),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth
    ),
) -> RunList:
    if not BaseRunsApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseRunsApi.subclasses[0]().list_runs(limit, cursor, status, client_id)


@router.post(
    "/api/v1/runs",
    responses={
        202: {"model": RunRef, "description": "Accepted"},
        400: {"model": Error, "description": "Invalid input"},
        409: {"model": Error, "description": "Conflict (e.g., idempotency-key reuse with different body)"},
    },
    tags=["Runs"],
    summary="Start a run using the in-memory workflow snapshot",
    response_model_by_alias=True,
)
async def start_run(
    run_start_request: RunStartRequest = Body(None, description=""),
    idempotency_key: Annotated[Optional[Annotated[str, Field(max_length=64)]], Field(description="Optional idempotency key for safe retries; if reused with a different body, return 409")] = Header(None, description="Optional idempotency key for safe retries; if reused with a different body, return 409", max_length=64),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth
    ),
) -> RunRef:
    if not BaseRunsApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseRunsApi.subclasses[0]().start_run(run_start_request, idempotency_key)


@router.get(
    "/api/v1/runs/{runId}",
    responses={
        200: {"model": Run, "description": "OK"},
        404: {"model": Error, "description": "Resource not found"},
    },
    tags=["Runs"],
    summary="Get run summary",
    response_model_by_alias=True,
)
async def get_run(
    runId: StrictStr = Path(..., description=""),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth
    ),
) -> Run:
    if not BaseRunsApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseRunsApi.subclasses[0]().get_run(runId)


@router.post(
    "/api/v1/runs/{runId}/cancel",
    responses={
        202: {"model": RunRef, "description": "Accepted"},
        404: {"model": Error, "description": "Resource not found"},
    },
    tags=["Runs"],
    summary="Cancel a run",
    response_model_by_alias=True,
)
async def cancel_run(
    runId: StrictStr = Path(..., description=""),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth
    ),
) -> RunRef:
    if not BaseRunsApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseRunsApi.subclasses[0]().cancel_run(runId)


@router.get(
    "/api/v1/runs/{runId}/definition",
    responses={
        200: {"model": Workflow, "description": "OK"},
        404: {"model": Error, "description": "Resource not found"},
    },
    tags=["Runs"],
    summary="Get the immutable workflow snapshot used by this run",
    response_model_by_alias=True,
)
async def get_run_definition(
    runId: StrictStr = Path(..., description=""),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth
    ),
) -> Workflow:
    if not BaseRunsApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseRunsApi.subclasses[0]().get_run_definition(runId)
