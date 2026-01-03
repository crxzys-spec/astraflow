from __future__ import annotations

from typing import Optional

from scheduler_api.http.errors import bad_request, forbidden
from pydantic import StrictStr

from scheduler_api.apis.package_permissions_api_base import BasePackagePermissionsApi
from scheduler_api.auth.roles import WORKFLOW_EDIT_ROLES, WORKFLOW_VIEW_ROLES, require_roles
from scheduler_api.models.package_permission import PackagePermission
from scheduler_api.models.package_permission_create_request import PackagePermissionCreateRequest
from scheduler_api.models.package_permission_list import PackagePermissionList
from scheduler_api.domain.resources import StoredPackagePermission
from scheduler_api.service.facade import resource_services


class PackagePermissionsApiImpl(BasePackagePermissionsApi):
    async def list_package_permissions(
        self,
        package_name: Optional[StrictStr],
    ) -> PackagePermissionList:
        token = require_roles(*WORKFLOW_VIEW_ROLES)
        owner_id = token.sub if token else None
        if not owner_id:
            raise forbidden("Authentication required.")
        permissions = resource_services.package_permissions.list(
            owner_id=owner_id,
            package_name=str(package_name) if package_name else None,
        )
        return PackagePermissionList(items=[_to_permission_model(item) for item in permissions])

    async def create_package_permission(
        self,
        package_permission_create_request: PackagePermissionCreateRequest,
    ) -> PackagePermission:
        token = require_roles(*WORKFLOW_EDIT_ROLES)
        if package_permission_create_request is None:
            raise bad_request("Missing permission payload.")
        payload = package_permission_create_request.model_dump(by_alias=True, exclude_none=True)
        package_name = payload.get("packageName") or package_permission_create_request.package_name
        permission_key = payload.get("permissionKey") or package_permission_create_request.permission_key
        types = payload.get("types") or package_permission_create_request.types
        actions = payload.get("actions") or package_permission_create_request.actions
        providers = payload.get("providers") or package_permission_create_request.providers
        if not package_name or not permission_key or not types:
            raise bad_request("Missing permission fields.")
        if not actions:
            actions = ["read"]
        stored = resource_services.package_permissions.upsert(
            owner_id=token.sub if token else "",
            package_name=str(package_name),
            permission_key=str(permission_key),
            types=[str(item) for item in types],
            actions=[str(item) for item in actions],
            providers=[str(item) for item in providers] if providers else None,
        )
        return _to_permission_model(stored)

    async def delete_package_permission(self, permissionId: StrictStr) -> None:
        token = require_roles(*WORKFLOW_EDIT_ROLES)
        resource_services.package_permissions.delete(str(permissionId), owner_id=token.sub if token else "")
        return None


def _to_permission_model(permission: StoredPackagePermission) -> PackagePermission:
    return PackagePermission(
        permission_id=permission.permission_id,
        owner_id=permission.owner_id,
        package_name=permission.package_name,
        permission_key=permission.permission_key,
        types=permission.types,
        providers=permission.providers,
        actions=permission.actions,
        created_at=permission.created_at,
    )
