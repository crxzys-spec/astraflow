# coding: utf-8

from typing import ClassVar, Dict, List, Tuple, Any  # noqa: F401
from fastapi import UploadFile

from pydantic import Field, StrictBytes, StrictStr
from typing import Any, List, Optional, Tuple, Union
from typing_extensions import Annotated
from hub_api.models.error import Error
from hub_api.models.hub_package_detail import HubPackageDetail
from hub_api.models.package_list_response import PackageListResponse
from hub_api.models.package_permission import PackagePermission
from hub_api.models.package_permission_create_request import PackagePermissionCreateRequest
from hub_api.models.package_permission_list import PackagePermissionList
from hub_api.models.package_permission_update_request import PackagePermissionUpdateRequest
from hub_api.models.package_registry import PackageRegistry
from hub_api.models.package_reserve_request import PackageReserveRequest
from hub_api.models.package_tag_request import PackageTagRequest
from hub_api.models.package_transfer_request import PackageTransferRequest
from hub_api.models.package_version_detail import PackageVersionDetail
from hub_api.models.package_visibility_request import PackageVisibilityRequest
from hub_api.models.visibility import Visibility
from hub_api.security_api import get_token_bearerAuth

class BasePackagesApi:
    subclasses: ClassVar[Tuple] = ()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        BasePackagesApi.subclasses = BasePackagesApi.subclasses + (cls,)
    async def list_packages(
        self,
        q: Annotated[Optional[StrictStr], Field(description="Search query")],
        tag: Annotated[Optional[StrictStr], Field(description="Filter by tag")],
        owner: Annotated[Optional[StrictStr], Field(description="Filter by owner id")],
        page: Annotated[Optional[Annotated[int, Field(ge=1)]], Field(description="1-based page index")],
        page_size: Annotated[Optional[Annotated[int, Field(le=200, ge=1)]], Field(description="Page size")],
    ) -> PackageListResponse:
        ...


    async def publish_package(
        self,
        file: UploadFile,
        visibility: Optional[Visibility],
        summary: Optional[StrictStr],
        readme: Optional[StrictStr],
        tags: Optional[List[StrictStr]],
    ) -> PackageVersionDetail:
        ...


    async def get_package(
        self,
        name: StrictStr,
    ) -> HubPackageDetail:
        ...


    async def reserve_package(
        self,
        name: StrictStr,
        package_reserve_request: Optional[PackageReserveRequest],
    ) -> PackageRegistry:
        ...


    async def get_package_version(
        self,
        name: StrictStr,
        version: StrictStr,
    ) -> PackageVersionDetail:
        ...


    async def download_package_archive(
        self,
        name: StrictStr,
        version: Annotated[Optional[StrictStr], Field(description="Optional version to download")],
    ) -> Any:
        ...


    async def set_package_tag(
        self,
        name: StrictStr,
        tag: StrictStr,
        package_tag_request: PackageTagRequest,
    ) -> None:
        ...


    async def delete_package_tag(
        self,
        name: StrictStr,
        tag: StrictStr,
    ) -> None:
        ...


    async def update_package_visibility(
        self,
        name: StrictStr,
        package_visibility_request: PackageVisibilityRequest,
    ) -> PackageRegistry:
        ...


    async def transfer_package(
        self,
        name: StrictStr,
        package_transfer_request: PackageTransferRequest,
    ) -> PackageRegistry:
        ...


    async def list_package_permissions(
        self,
        name: StrictStr,
    ) -> PackagePermissionList:
        ...


    async def add_package_permission(
        self,
        name: StrictStr,
        package_permission_create_request: PackagePermissionCreateRequest,
    ) -> PackagePermission:
        ...


    async def delete_package_permission(
        self,
        name: StrictStr,
        permissionId: StrictStr,
    ) -> None:
        ...


    async def update_package_permission(
        self,
        name: StrictStr,
        permissionId: StrictStr,
        package_permission_update_request: PackagePermissionUpdateRequest,
    ) -> PackagePermission:
        ...
