# coding: utf-8

from typing import Dict, List, Any  # noqa: F401
import importlib
import pkgutil

from hub_api.apis.teams_api_base import BaseTeamsApi
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
from hub_api.models.team import Team
from hub_api.models.team_create_request import TeamCreateRequest
from hub_api.models.team_list import TeamList
from hub_api.models.team_member import TeamMember
from hub_api.models.team_member_list import TeamMemberList
from hub_api.models.team_member_request import TeamMemberRequest
from hub_api.models.team_update_request import TeamUpdateRequest
from hub_api.security_api import get_token_bearerAuth

router = APIRouter()

ns_pkg = hub_api.impl
for _, name, _ in pkgutil.iter_modules(ns_pkg.__path__, ns_pkg.__name__ + "."):
    importlib.import_module(name)


@router.get(
    "/api/v1/orgs/{orgId}/teams",
    responses={
        200: {"model": TeamList, "description": "OK"},
        401: {"model": Error, "description": "Unauthorized"},
        404: {"model": Error, "description": "Not Found"},
    },
    tags=["Teams"],
    summary="List organization teams",
    response_model_by_alias=True,
)
async def list_organization_teams(
    orgId: StrictStr = Path(..., description=""),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth, scopes=["publish"]
    ),
) -> TeamList:
    if not BaseTeamsApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseTeamsApi.subclasses[0]().list_organization_teams(orgId)


@router.post(
    "/api/v1/orgs/{orgId}/teams",
    responses={
        201: {"model": Team, "description": "Created"},
        400: {"model": Error, "description": "Invalid input"},
        401: {"model": Error, "description": "Unauthorized"},
        403: {"model": Error, "description": "Forbidden"},
        404: {"model": Error, "description": "Not Found"},
    },
    tags=["Teams"],
    summary="Create team",
    response_model_by_alias=True,
)
async def create_team(
    orgId: StrictStr = Path(..., description=""),
    team_create_request: TeamCreateRequest = Body(None, description=""),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth, scopes=["publish"]
    ),
) -> Team:
    if not BaseTeamsApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseTeamsApi.subclasses[0]().create_team(orgId, team_create_request)


@router.patch(
    "/api/v1/orgs/{orgId}/teams/{teamId}",
    responses={
        200: {"model": Team, "description": "OK"},
        400: {"model": Error, "description": "Invalid input"},
        401: {"model": Error, "description": "Unauthorized"},
        403: {"model": Error, "description": "Forbidden"},
        404: {"model": Error, "description": "Not Found"},
        409: {"model": Error, "description": "Conflict"},
    },
    tags=["Teams"],
    summary="Update team",
    response_model_by_alias=True,
)
async def update_team(
    orgId: StrictStr = Path(..., description=""),
    teamId: StrictStr = Path(..., description=""),
    team_update_request: TeamUpdateRequest = Body(None, description=""),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth, scopes=["publish"]
    ),
) -> Team:
    if not BaseTeamsApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseTeamsApi.subclasses[0]().update_team(orgId, teamId, team_update_request)


@router.get(
    "/api/v1/orgs/{orgId}/teams/{teamId}/members",
    responses={
        200: {"model": TeamMemberList, "description": "OK"},
        401: {"model": Error, "description": "Unauthorized"},
        404: {"model": Error, "description": "Not Found"},
    },
    tags=["Teams"],
    summary="List team members",
    response_model_by_alias=True,
)
async def list_team_members(
    orgId: StrictStr = Path(..., description=""),
    teamId: StrictStr = Path(..., description=""),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth, scopes=["publish"]
    ),
) -> TeamMemberList:
    if not BaseTeamsApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseTeamsApi.subclasses[0]().list_team_members(orgId, teamId)


@router.post(
    "/api/v1/orgs/{orgId}/teams/{teamId}/members",
    responses={
        201: {"model": TeamMember, "description": "Created"},
        400: {"model": Error, "description": "Invalid input"},
        401: {"model": Error, "description": "Unauthorized"},
        403: {"model": Error, "description": "Forbidden"},
        404: {"model": Error, "description": "Not Found"},
    },
    tags=["Teams"],
    summary="Add team member",
    response_model_by_alias=True,
)
async def add_team_member(
    orgId: StrictStr = Path(..., description=""),
    teamId: StrictStr = Path(..., description=""),
    team_member_request: TeamMemberRequest = Body(None, description=""),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth, scopes=["publish"]
    ),
) -> TeamMember:
    if not BaseTeamsApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseTeamsApi.subclasses[0]().add_team_member(orgId, teamId, team_member_request)


@router.delete(
    "/api/v1/orgs/{orgId}/teams/{teamId}/members/{userId}",
    responses={
        204: {"description": "Deleted"},
        401: {"model": Error, "description": "Unauthorized"},
        403: {"model": Error, "description": "Forbidden"},
        404: {"model": Error, "description": "Not Found"},
    },
    tags=["Teams"],
    summary="Remove team member",
    response_model_by_alias=True,
)
async def remove_team_member(
    orgId: StrictStr = Path(..., description=""),
    teamId: StrictStr = Path(..., description=""),
    userId: StrictStr = Path(..., description=""),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth, scopes=["publish"]
    ),
) -> None:
    if not BaseTeamsApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseTeamsApi.subclasses[0]().remove_team_member(orgId, teamId, userId)
