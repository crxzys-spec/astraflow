# coding: utf-8

from typing import Dict, List, Any  # noqa: F401
import importlib
import pkgutil

from scheduler_api.apis.registry_api_base import BaseRegistryApi
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
from typing import Any
from scheduler_api.models.error import Error
from scheduler_api.models.registry_account_link import RegistryAccountLink
from scheduler_api.models.registry_account_link_request import RegistryAccountLinkRequest
from scheduler_api.models.registry_workflow_import_request import RegistryWorkflowImportRequest
from scheduler_api.models.registry_workflow_import_response import RegistryWorkflowImportResponse
from scheduler_api.security_api import get_token_bearerAuth

router = APIRouter()

ns_pkg = scheduler_api.impl
for _, name, _ in pkgutil.iter_modules(ns_pkg.__path__, ns_pkg.__name__ + "."):
    importlib.import_module(name)


@router.get(
    "/api/v1/registry/account",
    responses={
        200: {"model": RegistryAccountLink, "description": "OK"},
        404: {"model": Error, "description": "Resource not found"},
    },
    tags=["Registry"],
    summary="Get linked registry account",
    response_model_by_alias=True,
)
async def get_registry_account(
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth
    ),
) -> RegistryAccountLink:
    if not BaseRegistryApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseRegistryApi.subclasses[0]().get_registry_account()


@router.post(
    "/api/v1/registry/account",
    responses={
        200: {"model": RegistryAccountLink, "description": "OK"},
        400: {"model": Error, "description": "Invalid input"},
    },
    tags=["Registry"],
    summary="Link registry account",
    response_model_by_alias=True,
)
async def link_registry_account(
    registry_account_link_request: RegistryAccountLinkRequest = Body(None, description=""),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth
    ),
) -> RegistryAccountLink:
    if not BaseRegistryApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseRegistryApi.subclasses[0]().link_registry_account(registry_account_link_request)


@router.delete(
    "/api/v1/registry/account",
    responses={
        204: {"description": "Deleted"},
        404: {"model": Error, "description": "Resource not found"},
    },
    tags=["Registry"],
    summary="Unlink registry account",
    response_model_by_alias=True,
)
async def unlink_registry_account(
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth
    ),
) -> None:
    if not BaseRegistryApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseRegistryApi.subclasses[0]().unlink_registry_account()


@router.post(
    "/api/v1/registry/workflows/import",
    responses={
        200: {"model": RegistryWorkflowImportResponse, "description": "OK"},
        400: {"model": Error, "description": "Invalid input"},
        404: {"model": Error, "description": "Resource not found"},
    },
    tags=["Registry"],
    summary="Import a registry workflow into the platform",
    response_model_by_alias=True,
)
async def import_registry_workflow(
    registry_workflow_import_request: RegistryWorkflowImportRequest = Body(None, description=""),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth
    ),
) -> RegistryWorkflowImportResponse:
    if not BaseRegistryApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseRegistryApi.subclasses[0]().import_registry_workflow(registry_workflow_import_request)
