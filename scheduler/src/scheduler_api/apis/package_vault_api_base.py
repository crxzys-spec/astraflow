# coding: utf-8

from typing import ClassVar, Dict, List, Tuple, Any  # noqa: F401

from pydantic import StrictStr
from typing import Any
from scheduler_api.models.error import Error
from scheduler_api.models.package_vault_list import PackageVaultList
from scheduler_api.models.package_vault_upsert_request import PackageVaultUpsertRequest
from scheduler_api.security_api import get_token_bearerAuth

class BasePackageVaultApi:
    subclasses: ClassVar[Tuple] = ()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        BasePackageVaultApi.subclasses = BasePackageVaultApi.subclasses + (cls,)
    async def list_package_vault(
        self,
        package_name: StrictStr,
    ) -> PackageVaultList:
        ...


    async def upsert_package_vault(
        self,
        package_vault_upsert_request: PackageVaultUpsertRequest,
    ) -> PackageVaultList:
        ...


    async def delete_package_vault_item(
        self,
        packageName: StrictStr,
        key: StrictStr,
    ) -> None:
        ...
