# coding: utf-8

from typing import ClassVar, Dict, List, Tuple, Any  # noqa: F401

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

class BaseTeamsApi:
    subclasses: ClassVar[Tuple] = ()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        BaseTeamsApi.subclasses = BaseTeamsApi.subclasses + (cls,)
    async def list_organization_teams(
        self,
        orgId: StrictStr,
    ) -> TeamList:
        ...


    async def create_team(
        self,
        orgId: StrictStr,
        team_create_request: TeamCreateRequest,
    ) -> Team:
        ...


    async def update_team(
        self,
        orgId: StrictStr,
        teamId: StrictStr,
        team_update_request: TeamUpdateRequest,
    ) -> Team:
        ...


    async def list_team_members(
        self,
        orgId: StrictStr,
        teamId: StrictStr,
    ) -> TeamMemberList:
        ...


    async def add_team_member(
        self,
        orgId: StrictStr,
        teamId: StrictStr,
        team_member_request: TeamMemberRequest,
    ) -> TeamMember:
        ...


    async def remove_team_member(
        self,
        orgId: StrictStr,
        teamId: StrictStr,
        userId: StrictStr,
    ) -> None:
        ...
