# coding: utf-8

from typing import ClassVar, Dict, List, Tuple, Any  # noqa: F401

from pydantic import StrictStr
from typing import Any, Optional
from scheduler_api.models.error import Error
from scheduler_api.models.package_permission import PackagePermission
from scheduler_api.models.package_permission_create_request import PackagePermissionCreateRequest
from scheduler_api.models.package_permission_list import PackagePermissionList
from scheduler_api.security_api import get_token_bearerAuth

class BasePackagePermissionsApi:
    subclasses: ClassVar[Tuple] = ()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        BasePackagePermissionsApi.subclasses = BasePackagePermissionsApi.subclasses + (cls,)
    async def list_package_permissions(
        self,
        package_name: Optional[StrictStr],
    ) -> PackagePermissionList:
        ...


    async def create_package_permission(
        self,
        package_permission_create_request: PackagePermissionCreateRequest,
    ) -> PackagePermission:
        ...


    async def delete_package_permission(
        self,
        permissionId: StrictStr,
    ) -> None:
        ...
