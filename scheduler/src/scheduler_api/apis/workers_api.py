# coding: utf-8

from typing import Dict, List  # noqa: F401
import importlib
import pkgutil

from scheduler_api.apis.workers_api_base import BaseWorkersApi
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
from scheduler_api.models.command_ref import CommandRef
from scheduler_api.models.error import Error
from scheduler_api.models.list_workers200_response import ListWorkers200Response
from scheduler_api.models.worker import Worker
from scheduler_api.models.worker_command import WorkerCommand
from scheduler_api.security_api import get_token_bearerAuth

router = APIRouter()

ns_pkg = scheduler_api.impl
for _, name, _ in pkgutil.iter_modules(ns_pkg.__path__, ns_pkg.__name__ + "."):
    importlib.import_module(name)


@router.get(
    "/api/v1/workers",
    responses={
        200: {"model": ListWorkers200Response, "description": "OK"},
    },
    tags=["Workers"],
    summary="List workers (scheduler view)",
    response_model_by_alias=True,
)
async def list_workers(
    queue: Optional[StrictStr] = Query(None, description="", alias="queue"),
    limit: Optional[Annotated[int, Field(le=200, ge=1)]] = Query(50, description="", alias="limit", ge=1, le=200),
    cursor: Optional[StrictStr] = Query(None, description="", alias="cursor"),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth
    ),
) -> ListWorkers200Response:
    if not BaseWorkersApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseWorkersApi.subclasses[0]().list_workers(queue, limit, cursor)


@router.get(
    "/api/v1/workers/{workerId}",
    responses={
        200: {"model": Worker, "description": "OK"},
        404: {"model": Error, "description": "Resource not found"},
    },
    tags=["Workers"],
    summary="Get worker snapshot",
    response_model_by_alias=True,
)
async def get_worker(
    workerId: StrictStr = Path(..., description=""),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth
    ),
) -> Worker:
    if not BaseWorkersApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseWorkersApi.subclasses[0]().get_worker(workerId)


@router.post(
    "/api/v1/workers/{workerId}/commands",
    responses={
        202: {"model": CommandRef, "description": "Accepted"},
        400: {"model": Error, "description": "Invalid input"},
        404: {"model": Error, "description": "Resource not found"},
    },
    tags=["Workers"],
    summary="Enqueue admin command (drain/rebind/pkg.install/pkg.uninstall)",
    response_model_by_alias=True,
)
async def send_worker_command(
    workerId: StrictStr = Path(..., description=""),
    worker_command: WorkerCommand = Body(None, description=""),
    idempotency_key: Annotated[Optional[Annotated[str, Field(strict=True, max_length=64)]], Field(description="Optional idempotency key for safe retries; if reused with a different body, return 409")] = Header(None, description="Optional idempotency key for safe retries; if reused with a different body, return 409", max_length=64),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth
    ),
) -> CommandRef:
    if not BaseWorkersApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseWorkersApi.subclasses[0]().send_worker_command(workerId, worker_command, idempotency_key)
