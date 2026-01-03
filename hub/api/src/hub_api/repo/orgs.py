from __future__ import annotations

from typing import Any

from sqlalchemy import select, update, or_

from hub_api.db.models import (
    HubOrganization,
    HubOrganizationMember,
    HubPackagePermission,
    HubTeam,
    HubTeamMember,
)
from hub_api.db.session import SessionLocal
from hub_api.repo.common import _now

def _org_from_model(org: HubOrganization) -> dict[str, Any]:
    return {
        "id": org.id,
        "name": org.name,
        "slug": org.slug,
        "ownerId": org.owner_id,
        "createdAt": org.created_at,
        "updatedAt": org.updated_at,
    }

def _org_member_from_model(member: HubOrganizationMember) -> dict[str, Any]:
    return {
        "userId": member.user_id,
        "role": member.role,
        "joinedAt": member.joined_at,
    }

def list_organizations(user_id: str) -> list[dict[str, Any]]:
    with SessionLocal() as session:
        org_ids = list(
            session.execute(
                select(HubOrganizationMember.org_id).where(
                    HubOrganizationMember.user_id == user_id
                )
            ).scalars()
        )
        if not org_ids:
            return []
        orgs = session.execute(
            select(HubOrganization).where(HubOrganization.id.in_(org_ids))
        ).scalars().all()
        return [_org_from_model(org) for org in orgs]

def create_organization(name: str, slug: str, owner_id: str) -> dict[str, Any]:
    org_id = slug
    with SessionLocal() as session:
        existing = session.get(HubOrganization, org_id)
        if existing:
            raise ValueError("org_exists")
        now = _now()
        org = HubOrganization(
            id=org_id,
            name=name,
            slug=slug,
            owner_id=owner_id,
            created_at=now,
            updated_at=now,
        )
        session.add(org)
        session.add(
            HubOrganizationMember(
                org_id=org_id,
                user_id=owner_id,
                role="owner",
                joined_at=now,
            )
        )
        session.commit()
        session.refresh(org)
        record = _org_from_model(org)
    return record

def get_organization(org_id: str) -> dict[str, Any] | None:
    with SessionLocal() as session:
        org = session.get(HubOrganization, org_id)
        if not org:
            return None
        return _org_from_model(org)

def list_org_members(org_id: str) -> list[dict[str, Any]]:
    with SessionLocal() as session:
        members = session.execute(
            select(HubOrganizationMember).where(HubOrganizationMember.org_id == org_id)
        ).scalars().all()
        return [_org_member_from_model(member) for member in members]

def get_org_role(org_id: str, user_id: str) -> str | None:
    with SessionLocal() as session:
        role = session.execute(
            select(HubOrganizationMember.role).where(
                HubOrganizationMember.org_id == org_id,
                HubOrganizationMember.user_id == user_id,
            )
        ).scalar_one_or_none()
        return role

def add_org_member(org_id: str, user_id: str, role: str) -> dict[str, Any]:
    with SessionLocal() as session:
        member = session.execute(
            select(HubOrganizationMember).where(
                HubOrganizationMember.org_id == org_id,
                HubOrganizationMember.user_id == user_id,
            )
        ).scalar_one_or_none()
        if member:
            member.role = role
        else:
            member = HubOrganizationMember(
                org_id=org_id,
                user_id=user_id,
                role=role,
                joined_at=_now(),
            )
            session.add(member)
        session.commit()
        session.refresh(member)
        return _org_member_from_model(member)

def remove_org_member(org_id: str, user_id: str) -> None:
    with SessionLocal() as session:
        member = session.execute(
            select(HubOrganizationMember).where(
                HubOrganizationMember.org_id == org_id,
                HubOrganizationMember.user_id == user_id,
            )
        ).scalar_one_or_none()
        if member:
            session.delete(member)
            session.commit()

def is_user_in_org(user_id: str, org_id: str) -> bool:
    with SessionLocal() as session:
        member = session.execute(
            select(HubOrganizationMember).where(
                HubOrganizationMember.org_id == org_id,
                HubOrganizationMember.user_id == user_id,
            )
        ).scalar_one_or_none()
        return member is not None

def update_organization(
    org_id: str,
    *,
    name: str | None,
    slug: str | None,
) -> dict[str, Any]:
    with SessionLocal() as session:
        org = session.get(HubOrganization, org_id)
        if not org:
            raise ValueError("org_not_found")
        target_name = org.name if name is None else name
        target_slug = org.slug if slug is None else slug
        if target_slug != org.slug:
            existing = session.execute(
                select(HubOrganization).where(
                    or_(
                        HubOrganization.slug == target_slug,
                        HubOrganization.id == target_slug,
                    ),
                    HubOrganization.id != org_id,
                )
            ).scalar_one_or_none()
            if existing:
                raise ValueError("org_exists")

            now = _now()
            new_org = HubOrganization(
                id=target_slug,
                name=target_name,
                slug=target_slug,
                owner_id=org.owner_id,
                created_at=org.created_at,
                updated_at=now,
            )
            session.add(new_org)
            session.flush()

            session.execute(
                update(HubOrganizationMember)
                .where(HubOrganizationMember.org_id == org.id)
                .values(org_id=target_slug)
            )
            session.execute(
                update(HubPackagePermission)
                .where(
                    HubPackagePermission.subject_type == "org",
                    HubPackagePermission.subject_id == org.id,
                )
                .values(subject_id=target_slug)
            )

            teams = session.execute(
                select(HubTeam).where(HubTeam.org_id == org.id)
            ).scalars().all()
            for team in teams:
                new_team_id = f"{target_slug}:{team.slug}"
                new_team = HubTeam(
                    id=new_team_id,
                    org_id=target_slug,
                    name=team.name,
                    slug=team.slug,
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

            session.delete(org)
            session.commit()
            session.refresh(new_org)
            return _org_from_model(new_org)

        updated = False
        if name is not None and name != org.name:
            org.name = name
            updated = True
        if updated:
            org.updated_at = _now()
        session.commit()
        session.refresh(org)
        return _org_from_model(org)
