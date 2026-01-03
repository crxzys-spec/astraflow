from __future__ import annotations

from typing import Any

from sqlalchemy import select, update

from hub_api.db.models import HubPackagePermission, HubTeam, HubTeamMember
from hub_api.db.session import SessionLocal
from hub_api.repo.common import _now

def _team_from_model(team: HubTeam) -> dict[str, Any]:
    return {
        "id": team.id,
        "orgId": team.org_id,
        "name": team.name,
        "slug": team.slug,
        "createdAt": team.created_at,
    }

def _team_member_from_model(member: HubTeamMember) -> dict[str, Any]:
    return {
        "userId": member.user_id,
        "addedAt": member.added_at,
    }

def list_org_teams(org_id: str) -> list[dict[str, Any]]:
    with SessionLocal() as session:
        teams = session.execute(
            select(HubTeam).where(HubTeam.org_id == org_id)
        ).scalars().all()
        return [_team_from_model(team) for team in teams]

def create_team(org_id: str, name: str, slug: str) -> dict[str, Any]:
    team_id = f"{org_id}:{slug}"
    with SessionLocal() as session:
        existing = session.get(HubTeam, team_id)
        if existing:
            raise ValueError("team_exists")
        team = HubTeam(
            id=team_id,
            org_id=org_id,
            name=name,
            slug=slug,
            created_at=_now(),
        )
        session.add(team)
        session.commit()
        session.refresh(team)
        return _team_from_model(team)

def list_team_members(team_id: str) -> list[dict[str, Any]]:
    with SessionLocal() as session:
        members = session.execute(
            select(HubTeamMember).where(HubTeamMember.team_id == team_id)
        ).scalars().all()
        return [_team_member_from_model(member) for member in members]

def add_team_member(team_id: str, user_id: str) -> dict[str, Any]:
    with SessionLocal() as session:
        member = session.execute(
            select(HubTeamMember).where(
                HubTeamMember.team_id == team_id,
                HubTeamMember.user_id == user_id,
            )
        ).scalar_one_or_none()
        if member:
            return _team_member_from_model(member)
        member = HubTeamMember(
            team_id=team_id,
            user_id=user_id,
            added_at=_now(),
        )
        session.add(member)
        session.commit()
        session.refresh(member)
        return _team_member_from_model(member)

def remove_team_member(team_id: str, user_id: str) -> None:
    with SessionLocal() as session:
        member = session.execute(
            select(HubTeamMember).where(
                HubTeamMember.team_id == team_id,
                HubTeamMember.user_id == user_id,
            )
        ).scalar_one_or_none()
        if member:
            session.delete(member)
            session.commit()

def is_user_in_team(user_id: str, team_id: str) -> bool:
    with SessionLocal() as session:
        member = session.execute(
            select(HubTeamMember).where(
                HubTeamMember.team_id == team_id,
                HubTeamMember.user_id == user_id,
            )
        ).scalar_one_or_none()
        return member is not None

def update_team(
    team_id: str,
    *,
    org_id: str,
    name: str | None,
    slug: str | None,
) -> dict[str, Any]:
    with SessionLocal() as session:
        team = session.get(HubTeam, team_id)
        if not team or team.org_id != org_id:
            raise ValueError("team_not_found")
        target_name = team.name if name is None else name
        target_slug = team.slug if slug is None else slug
        if target_slug != team.slug:
            existing = session.execute(
                select(HubTeam).where(
                    HubTeam.org_id == org_id,
                    HubTeam.slug == target_slug,
                    HubTeam.id != team_id,
                )
            ).scalar_one_or_none()
            if existing:
                raise ValueError("team_exists")
            new_team_id = f"{org_id}:{target_slug}"
            new_team = HubTeam(
                id=new_team_id,
                org_id=org_id,
                name=target_name,
                slug=target_slug,
                created_at=team.created_at,
            )
            session.add(new_team)
            session.flush()
            session.execute(
                update(HubTeamMember)
                .where(HubTeamMember.team_id == team.id)
                .values(team_id=new_team_id)
            )
            session.execute(
                update(HubPackagePermission)
                .where(
                    HubPackagePermission.subject_type == "team",
                    HubPackagePermission.subject_id == team.id,
                )
                .values(subject_id=new_team_id)
            )
            session.delete(team)
            session.commit()
            session.refresh(new_team)
            return _team_from_model(new_team)

        updated = False
        if name is not None and name != team.name:
            team.name = name
            updated = True
        if updated:
            session.commit()
        session.refresh(team)
        return _team_from_model(team)
