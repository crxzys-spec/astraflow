from __future__ import annotations

from fastapi import HTTPException, status

from hub_api.repo.audit import record_audit_event
from hub_api.repo.teams import (
    add_team_member,
    create_team,
    list_org_teams,
    list_team_members,
    remove_team_member,
    update_team,
)
from hub_api.repo.orgs import get_organization, get_org_role
from hub_api.models.team import Team
from hub_api.models.team_create_request import TeamCreateRequest
from hub_api.models.team_list import TeamList
from hub_api.models.team_member import TeamMember
from hub_api.models.team_member_list import TeamMemberList
from hub_api.models.team_member_request import TeamMemberRequest
from hub_api.models.team_update_request import TeamUpdateRequest
from hub_api.security_api import is_admin, require_actor


def _get_org_or_404(org_id: str) -> dict:
    record = get_organization(org_id)
    if not record:
        raise HTTPException(status_code=404, detail="Not Found")
    return record


def _require_org_member(org_id: str, actor_id: str) -> None:
    if is_admin():
        return
    if get_org_role(org_id, actor_id) is None:
        raise HTTPException(status_code=404, detail="Not Found")


def _require_org_admin(org_id: str, actor_id: str) -> None:
    if is_admin():
        return
    role = get_org_role(org_id, actor_id)
    if role not in ("owner", "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


def _get_team_in_org(org_id: str, team_id: str) -> dict:
    teams = list_org_teams(org_id)
    for team in teams:
        if team["id"] == team_id:
            return team
    raise HTTPException(status_code=404, detail="Not Found")


class TeamsService:
    async def list_organization_teams(
        self,
        orgId: str,
    ) -> TeamList:
        actor_id = require_actor()
        _get_org_or_404(orgId)
        _require_org_member(orgId, actor_id)
        teams = [Team.from_dict(team) for team in list_org_teams(orgId)]
        return TeamList(items=teams)

    async def create_team(
        self,
        orgId: str,
        team_create_request: TeamCreateRequest,
    ) -> Team:
        actor_id = require_actor()
        _get_org_or_404(orgId)
        _require_org_admin(orgId, actor_id)
        if team_create_request is None:
            raise HTTPException(status_code=400, detail="Payload is required.")
        try:
            team = create_team(orgId, team_create_request.name, team_create_request.slug)
        except ValueError as exc:
            if str(exc) == "team_exists":
                raise HTTPException(status_code=409, detail="Team already exists.") from exc
            raise HTTPException(status_code=400, detail="Unable to create team.") from exc
        record_audit_event(
            action="team.create",
            actor_id=actor_id,
            target_type="team",
            target_id=team.get("id"),
            metadata={
                "orgId": orgId,
                "slug": team.get("slug"),
                "name": team.get("name"),
            },
        )
        return Team.from_dict(team)

    async def update_team(
        self,
        orgId: str,
        teamId: str,
        team_update_request: TeamUpdateRequest,
    ) -> Team:
        actor_id = require_actor()
        _get_org_or_404(orgId)
        _require_org_admin(orgId, actor_id)
        previous = _get_team_in_org(orgId, teamId)
        if team_update_request is None:
            raise HTTPException(status_code=400, detail="Payload is required.")
        name = team_update_request.name
        slug = team_update_request.slug
        if name is not None:
            name = name.strip()
        if slug is not None:
            slug = slug.strip()
        if name == "":
            raise HTTPException(status_code=400, detail="name cannot be empty.")
        if slug == "":
            raise HTTPException(status_code=400, detail="slug cannot be empty.")
        if name is None and slug is None:
            raise HTTPException(status_code=400, detail="No changes provided.")
        try:
            updated = update_team(teamId, org_id=orgId, name=name, slug=slug)
        except ValueError as exc:
            if str(exc) == "team_not_found":
                raise HTTPException(status_code=404, detail="Not Found") from exc
            if str(exc) == "team_exists":
                raise HTTPException(status_code=409, detail="Team slug already exists.") from exc
            raise HTTPException(status_code=400, detail="Unable to update team.") from exc
        changes: dict[str, dict[str, str | None]] = {}
        if name is not None and name != previous.get("name"):
            changes["name"] = {"from": previous.get("name"), "to": name}
        if slug is not None and slug != previous.get("slug"):
            changes["slug"] = {"from": previous.get("slug"), "to": slug}
        if changes:
            metadata: dict[str, object] = {
                "orgId": orgId,
                "changes": changes,
            }
            if slug is not None and slug != previous.get("slug"):
                metadata["previousId"] = previous.get("id")
            record_audit_event(
                action="team.update",
                actor_id=actor_id,
                target_type="team",
                target_id=updated.get("id"),
                metadata=metadata,
            )
        return Team.from_dict(updated)

    async def list_team_members(
        self,
        orgId: str,
        teamId: str,
    ) -> TeamMemberList:
        actor_id = require_actor()
        _get_org_or_404(orgId)
        _require_org_member(orgId, actor_id)
        _get_team_in_org(orgId, teamId)
        members = [TeamMember.from_dict(member) for member in list_team_members(teamId)]
        return TeamMemberList(items=members)

    async def add_team_member(
        self,
        orgId: str,
        teamId: str,
        team_member_request: TeamMemberRequest,
    ) -> TeamMember:
        actor_id = require_actor()
        _get_org_or_404(orgId)
        _require_org_admin(orgId, actor_id)
        _get_team_in_org(orgId, teamId)
        if team_member_request is None or not team_member_request.user_id:
            raise HTTPException(status_code=400, detail="userId is required.")
        member = add_team_member(teamId, team_member_request.user_id)
        record_audit_event(
            action="team.member.add",
            actor_id=actor_id,
            target_type="team",
            target_id=teamId,
            metadata={
                "orgId": orgId,
                "userId": team_member_request.user_id,
            },
        )
        return TeamMember.from_dict(member)

    async def remove_team_member(
        self,
        orgId: str,
        teamId: str,
        userId: str,
    ) -> None:
        actor_id = require_actor()
        _get_org_or_404(orgId)
        _require_org_admin(orgId, actor_id)
        _get_team_in_org(orgId, teamId)
        remove_team_member(teamId, userId)
        record_audit_event(
            action="team.member.remove",
            actor_id=actor_id,
            target_type="team",
            target_id=teamId,
            metadata={
                "orgId": orgId,
                "userId": userId,
            },
        )
        return None
