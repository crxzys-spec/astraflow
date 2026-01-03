# coding: utf-8

from typing import Dict, List, Any  # noqa: F401
import importlib
import pkgutil

from hub_api.apis.orgs_api_base import BaseOrgsApi
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
from pydantic import StrictStr
from typing import Any
from hub_api.models.error import Error
from hub_api.models.organization import Organization
from hub_api.models.organization_create_request import OrganizationCreateRequest
from hub_api.models.organization_list import OrganizationList
from hub_api.models.organization_member import OrganizationMember
from hub_api.models.organization_member_list import OrganizationMemberList
from hub_api.models.organization_member_request import OrganizationMemberRequest
from hub_api.models.organization_update_request import OrganizationUpdateRequest
from hub_api.security_api import get_token_bearerAuth

router = APIRouter()

ns_pkg = hub_api.impl
for _, name, _ in pkgutil.iter_modules(ns_pkg.__path__, ns_pkg.__name__ + "."):
    importlib.import_module(name)


@router.get(
    "/api/v1/orgs",
    responses={
        200: {"model": OrganizationList, "description": "OK"},
        401: {"model": Error, "description": "Unauthorized"},
    },
    tags=["Orgs"],
    summary="List organizations",
    response_model_by_alias=True,
)
async def list_organizations(
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth, scopes=["publish"]
    ),
) -> OrganizationList:
    if not BaseOrgsApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseOrgsApi.subclasses[0]().list_organizations()


@router.post(
    "/api/v1/orgs",
    responses={
        201: {"model": Organization, "description": "Created"},
        400: {"model": Error, "description": "Invalid input"},
        401: {"model": Error, "description": "Unauthorized"},
        409: {"model": Error, "description": "Conflict"},
    },
    tags=["Orgs"],
    summary="Create organization",
    response_model_by_alias=True,
)
async def create_organization(
    organization_create_request: OrganizationCreateRequest = Body(None, description=""),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth, scopes=["publish"]
    ),
) -> Organization:
    if not BaseOrgsApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseOrgsApi.subclasses[0]().create_organization(organization_create_request)


@router.get(
    "/api/v1/orgs/{orgId}",
    responses={
        200: {"model": Organization, "description": "OK"},
        401: {"model": Error, "description": "Unauthorized"},
        404: {"model": Error, "description": "Not Found"},
    },
    tags=["Orgs"],
    summary="Get organization",
    response_model_by_alias=True,
)
async def get_organization(
    orgId: StrictStr = Path(..., description=""),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth, scopes=["publish"]
    ),
) -> Organization:
    if not BaseOrgsApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseOrgsApi.subclasses[0]().get_organization(orgId)


@router.patch(
    "/api/v1/orgs/{orgId}",
    responses={
        200: {"model": Organization, "description": "OK"},
        400: {"model": Error, "description": "Invalid input"},
        401: {"model": Error, "description": "Unauthorized"},
        403: {"model": Error, "description": "Forbidden"},
        404: {"model": Error, "description": "Not Found"},
        409: {"model": Error, "description": "Conflict"},
    },
    tags=["Orgs"],
    summary="Update organization",
    response_model_by_alias=True,
)
async def update_organization(
    orgId: StrictStr = Path(..., description=""),
    organization_update_request: OrganizationUpdateRequest = Body(None, description=""),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth, scopes=["publish"]
    ),
) -> Organization:
    if not BaseOrgsApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseOrgsApi.subclasses[0]().update_organization(orgId, organization_update_request)


@router.get(
    "/api/v1/orgs/{orgId}/members",
    responses={
        200: {"model": OrganizationMemberList, "description": "OK"},
        401: {"model": Error, "description": "Unauthorized"},
        404: {"model": Error, "description": "Not Found"},
    },
    tags=["Orgs"],
    summary="List organization members",
    response_model_by_alias=True,
)
async def list_organization_members(
    orgId: StrictStr = Path(..., description=""),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth, scopes=["publish"]
    ),
) -> OrganizationMemberList:
    if not BaseOrgsApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseOrgsApi.subclasses[0]().list_organization_members(orgId)


@router.post(
    "/api/v1/orgs/{orgId}/members",
    responses={
        201: {"model": OrganizationMember, "description": "Created"},
        400: {"model": Error, "description": "Invalid input"},
        401: {"model": Error, "description": "Unauthorized"},
        403: {"model": Error, "description": "Forbidden"},
        404: {"model": Error, "description": "Not Found"},
    },
    tags=["Orgs"],
    summary="Add organization member",
    response_model_by_alias=True,
)
async def add_organization_member(
    orgId: StrictStr = Path(..., description=""),
    organization_member_request: OrganizationMemberRequest = Body(None, description=""),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth, scopes=["publish"]
    ),
) -> OrganizationMember:
    if not BaseOrgsApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseOrgsApi.subclasses[0]().add_organization_member(orgId, organization_member_request)


@router.delete(
    "/api/v1/orgs/{orgId}/members/{userId}",
    responses={
        204: {"description": "Deleted"},
        401: {"model": Error, "description": "Unauthorized"},
        403: {"model": Error, "description": "Forbidden"},
        404: {"model": Error, "description": "Not Found"},
    },
    tags=["Orgs"],
    summary="Remove organization member",
    response_model_by_alias=True,
)
async def remove_organization_member(
    orgId: StrictStr = Path(..., description=""),
    userId: StrictStr = Path(..., description=""),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth, scopes=["publish"]
    ),
) -> None:
    if not BaseOrgsApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseOrgsApi.subclasses[0]().remove_organization_member(orgId, userId)
