from __future__ import annotations

from hub_api.apis.teams_api_base import BaseTeamsApi
from hub_api.models.team import Team
from hub_api.models.team_create_request import TeamCreateRequest
from hub_api.models.team_list import TeamList
from hub_api.models.team_member import TeamMember
from hub_api.models.team_member_list import TeamMemberList
from hub_api.models.team_member_request import TeamMemberRequest
from hub_api.models.team_update_request import TeamUpdateRequest
from hub_api.services.teams_service import TeamsService

_service = TeamsService()


class TeamsApiImpl(BaseTeamsApi):
    async def list_organization_teams(
        self,
        orgId: str,
    ) -> TeamList:
        return await _service.list_organization_teams(orgId)

    async def create_team(
        self,
        orgId: str,
        team_create_request: TeamCreateRequest,
    ) -> Team:
        return await _service.create_team(orgId, team_create_request)

    async def update_team(
        self,
        orgId: str,
        teamId: str,
        team_update_request: TeamUpdateRequest,
    ) -> Team:
        return await _service.update_team(orgId, teamId, team_update_request)

    async def list_team_members(
        self,
        orgId: str,
        teamId: str,
    ) -> TeamMemberList:
        return await _service.list_team_members(orgId, teamId)

    async def add_team_member(
        self,
        orgId: str,
        teamId: str,
        team_member_request: TeamMemberRequest,
    ) -> TeamMember:
        return await _service.add_team_member(orgId, teamId, team_member_request)

    async def remove_team_member(
        self,
        orgId: str,
        teamId: str,
        userId: str,
    ) -> None:
        return await _service.remove_team_member(orgId, teamId, userId)
