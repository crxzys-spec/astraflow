# coding: utf-8

from typing import ClassVar, Dict, List, Tuple, Any  # noqa: F401

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

class BaseOrgsApi:
    subclasses: ClassVar[Tuple] = ()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        BaseOrgsApi.subclasses = BaseOrgsApi.subclasses + (cls,)
    async def list_organizations(
        self,
    ) -> OrganizationList:
        ...


    async def create_organization(
        self,
        organization_create_request: OrganizationCreateRequest,
    ) -> Organization:
        ...


    async def get_organization(
        self,
        orgId: StrictStr,
    ) -> Organization:
        ...


    async def update_organization(
        self,
        orgId: StrictStr,
        organization_update_request: OrganizationUpdateRequest,
    ) -> Organization:
        ...


    async def list_organization_members(
        self,
        orgId: StrictStr,
    ) -> OrganizationMemberList:
        ...


    async def add_organization_member(
        self,
        orgId: StrictStr,
        organization_member_request: OrganizationMemberRequest,
    ) -> OrganizationMember:
        ...


    async def remove_organization_member(
        self,
        orgId: StrictStr,
        userId: StrictStr,
    ) -> None:
        ...
