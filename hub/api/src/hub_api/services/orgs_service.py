from __future__ import annotations

from fastapi import HTTPException, status

from hub_api.repo.audit import record_audit_event
from hub_api.repo.orgs import (
    add_org_member,
    create_organization,
    get_organization,
    get_org_role,
    list_organizations,
    list_org_members,
    remove_org_member,
    update_organization,
)
from hub_api.models.organization import Organization
from hub_api.models.organization_create_request import OrganizationCreateRequest
from hub_api.models.organization_list import OrganizationList
from hub_api.models.organization_member import OrganizationMember
from hub_api.models.organization_member_list import OrganizationMemberList
from hub_api.models.organization_member_request import OrganizationMemberRequest
from hub_api.models.organization_update_request import OrganizationUpdateRequest
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


def _role_value(role) -> str:
    return role.value if hasattr(role, "value") else str(role)


class OrgsService:
    async def list_organizations(self) -> OrganizationList:
        actor_id = require_actor()
        items = [Organization.from_dict(record) for record in list_organizations(actor_id)]
        return OrganizationList(items=items)

    async def create_organization(
        self,
        organization_create_request: OrganizationCreateRequest,
    ) -> Organization:
        actor_id = require_actor()
        if organization_create_request is None:
            raise HTTPException(status_code=400, detail="Payload is required.")
        try:
            record = create_organization(
                organization_create_request.name,
                organization_create_request.slug,
                actor_id,
            )
        except ValueError as exc:
            if str(exc) == "org_exists":
                raise HTTPException(status_code=409, detail="Organization already exists.") from exc
            raise HTTPException(status_code=400, detail="Unable to create organization.") from exc
        record_audit_event(
            action="org.create",
            actor_id=actor_id,
            target_type="org",
            target_id=record.get("id"),
            metadata={"name": record.get("name")},
        )
        return Organization.from_dict(record)

    async def get_organization(
        self,
        orgId: str,
    ) -> Organization:
        actor_id = require_actor()
        _get_org_or_404(orgId)
        _require_org_member(orgId, actor_id)
        record = get_organization(orgId)
        return Organization.from_dict(record)

    async def update_organization(
        self,
        orgId: str,
        organization_update_request: OrganizationUpdateRequest,
    ) -> Organization:
        actor_id = require_actor()
        record = _get_org_or_404(orgId)
        _require_org_admin(orgId, actor_id)
        if organization_update_request is None:
            raise HTTPException(status_code=400, detail="Payload is required.")
        name = organization_update_request.name
        slug = organization_update_request.slug
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
            updated = update_organization(orgId, name=name, slug=slug)
        except ValueError as exc:
            if str(exc) == "org_not_found":
                raise HTTPException(status_code=404, detail="Not Found") from exc
            if str(exc) == "org_exists":
                raise HTTPException(status_code=409, detail="Organization slug already exists.") from exc
            raise HTTPException(status_code=400, detail="Unable to update organization.") from exc
        changes: dict[str, dict[str, str | None]] = {}
        if name is not None and name != record.get("name"):
            changes["name"] = {"from": record.get("name"), "to": name}
        if slug is not None and slug != record.get("slug"):
            changes["slug"] = {"from": record.get("slug"), "to": slug}
        if changes:
            metadata: dict[str, object] = {"changes": changes}
            if slug is not None and slug != record.get("slug"):
                metadata["previousId"] = record.get("id")
            record_audit_event(
                action="org.update",
                actor_id=actor_id,
                target_type="org",
                target_id=updated.get("id"),
                metadata=metadata,
            )
        return Organization.from_dict(updated)

    async def list_organization_members(
        self,
        orgId: str,
    ) -> OrganizationMemberList:
        actor_id = require_actor()
        _get_org_or_404(orgId)
        _require_org_member(orgId, actor_id)
        members = [OrganizationMember.from_dict(member) for member in list_org_members(orgId)]
        return OrganizationMemberList(items=members)

    async def add_organization_member(
        self,
        orgId: str,
        organization_member_request: OrganizationMemberRequest,
    ) -> OrganizationMember:
        actor_id = require_actor()
        _get_org_or_404(orgId)
        _require_org_admin(orgId, actor_id)
        if organization_member_request is None or not organization_member_request.user_id:
            raise HTTPException(status_code=400, detail="userId is required.")
        role_value = _role_value(organization_member_request.role)
        member = add_org_member(orgId, organization_member_request.user_id, role_value)
        record_audit_event(
            action="org.member.add",
            actor_id=actor_id,
            target_type="org",
            target_id=orgId,
            metadata={
                "userId": organization_member_request.user_id,
                "role": role_value,
            },
        )
        return OrganizationMember.from_dict(member)

    async def remove_organization_member(
        self,
        orgId: str,
        userId: str,
    ) -> None:
        actor_id = require_actor()
        _get_org_or_404(orgId)
        _require_org_admin(orgId, actor_id)
        remove_org_member(orgId, userId)
        record_audit_event(
            action="org.member.remove",
            actor_id=actor_id,
            target_type="org",
            target_id=orgId,
            metadata={
                "userId": userId,
            },
        )
        return None
