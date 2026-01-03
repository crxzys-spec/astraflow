from __future__ import annotations

from fastapi import UploadFile
from fastapi.responses import Response

from hub_api.apis.packages_api_base import BasePackagesApi
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
from hub_api.services.packages_service import PackagesService

_service = PackagesService()


class PackagesApiImpl(BasePackagesApi):
    async def list_packages(
        self,
        q: str | None,
        tag: str | None,
        owner: str | None,
        page: int | None,
        page_size: int | None,
    ) -> PackageListResponse:
        return await _service.list_packages(q, tag, owner, page, page_size)

    async def publish_package(
        self,
        file: UploadFile,
        visibility: Visibility | None,
        summary: str | None,
        readme: str | None,
        tags: list[str] | None,
    ) -> PackageVersionDetail:
        return await _service.publish_package(file, visibility, summary, readme, tags)

    async def get_package(
        self,
        name: str,
    ) -> HubPackageDetail:
        return await _service.get_package(name)

    async def reserve_package(
        self,
        name: str,
        package_reserve_request: PackageReserveRequest | None,
    ) -> PackageRegistry:
        return await _service.reserve_package(name, package_reserve_request)

    async def get_package_version(
        self,
        name: str,
        version: str,
    ) -> PackageVersionDetail:
        return await _service.get_package_version(name, version)

    async def download_package_archive(
        self,
        name: str,
        version: str | None,
    ) -> Response:
        return await _service.download_package_archive(name, version)

    async def set_package_tag(
        self,
        name: str,
        tag: str,
        package_tag_request: PackageTagRequest,
    ) -> None:
        return await _service.set_package_tag(name, tag, package_tag_request)

    async def delete_package_tag(
        self,
        name: str,
        tag: str,
    ) -> None:
        return await _service.delete_package_tag(name, tag)

    async def update_package_visibility(
        self,
        name: str,
        package_visibility_request: PackageVisibilityRequest,
    ) -> PackageRegistry:
        return await _service.update_package_visibility(name, package_visibility_request)

    async def transfer_package(
        self,
        name: str,
        package_transfer_request: PackageTransferRequest,
    ) -> PackageRegistry:
        return await _service.transfer_package(name, package_transfer_request)

    async def list_package_permissions(
        self,
        name: str,
    ) -> PackagePermissionList:
        return await _service.list_package_permissions(name)

    async def add_package_permission(
        self,
        name: str,
        package_permission_create_request: PackagePermissionCreateRequest,
    ) -> PackagePermission:
        return await _service.add_package_permission(name, package_permission_create_request)

    async def delete_package_permission(
        self,
        name: str,
        permissionId: str,
    ) -> None:
        return await _service.delete_package_permission(name, permissionId)

    async def update_package_permission(
        self,
        name: str,
        permissionId: str,
        package_permission_update_request: PackagePermissionUpdateRequest,
    ) -> PackagePermission:
        return await _service.update_package_permission(
            name,
            permissionId,
            package_permission_update_request,
        )
