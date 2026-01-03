from __future__ import annotations

from hub_api.apis.orgs_api_base import BaseOrgsApi
from hub_api.models.organization import Organization
from hub_api.models.organization_create_request import OrganizationCreateRequest
from hub_api.models.organization_list import OrganizationList
from hub_api.models.organization_member import OrganizationMember
from hub_api.models.organization_member_list import OrganizationMemberList
from hub_api.models.organization_member_request import OrganizationMemberRequest
from hub_api.models.organization_update_request import OrganizationUpdateRequest
from hub_api.services.orgs_service import OrgsService

_service = OrgsService()


class OrgsApiImpl(BaseOrgsApi):
    async def list_organizations(self) -> OrganizationList:
        return await _service.list_organizations()

    async def create_organization(
        self,
        organization_create_request: OrganizationCreateRequest,
    ) -> Organization:
        return await _service.create_organization(organization_create_request)

    async def get_organization(
        self,
        orgId: str,
    ) -> Organization:
        return await _service.get_organization(orgId)

    async def update_organization(
        self,
        orgId: str,
        organization_update_request: OrganizationUpdateRequest,
    ) -> Organization:
        return await _service.update_organization(orgId, organization_update_request)

    async def list_organization_members(
        self,
        orgId: str,
    ) -> OrganizationMemberList:
        return await _service.list_organization_members(orgId)

    async def add_organization_member(
        self,
        orgId: str,
        organization_member_request: OrganizationMemberRequest,
    ) -> OrganizationMember:
        return await _service.add_organization_member(orgId, organization_member_request)

    async def remove_organization_member(
        self,
        orgId: str,
        userId: str,
    ) -> None:
        return await _service.remove_organization_member(orgId, userId)
