# coding: utf-8

from typing import ClassVar, Dict, List, Tuple, Any  # noqa: F401
from fastapi import UploadFile

from pydantic import Field, StrictBytes, StrictStr
from typing import Any, Optional, Tuple, Union
from typing_extensions import Annotated
from scheduler_api.models.error import Error
from scheduler_api.models.package_detail import PackageDetail
from scheduler_api.models.package_list import PackageList
from scheduler_api.models.published_package_gc_request import PublishedPackageGcRequest
from scheduler_api.models.published_package_gc_result import PublishedPackageGcResult
from scheduler_api.models.published_package_registry import PublishedPackageRegistry
from scheduler_api.models.published_package_reserve_request import PublishedPackageReserveRequest
from scheduler_api.models.published_package_status_request import PublishedPackageStatusRequest
from scheduler_api.models.published_package_tag_request import PublishedPackageTagRequest
from scheduler_api.models.published_package_transfer_request import PublishedPackageTransferRequest
from scheduler_api.models.published_package_visibility_request import PublishedPackageVisibilityRequest
from scheduler_api.security_api import get_token_bearerAuth

class BasePublishedPackagesApi:
    subclasses: ClassVar[Tuple] = ()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        BasePublishedPackagesApi.subclasses = BasePublishedPackagesApi.subclasses + (cls,)
    async def list_published_packages(
        self,
    ) -> PackageList:
        ...


    async def upload_published_package(
        self,
        file: UploadFile,
    ) -> PackageDetail:
        ...


    async def gc_published_packages(
        self,
        published_package_gc_request: PublishedPackageGcRequest,
    ) -> PublishedPackageGcResult:
        ...


    async def get_published_package(
        self,
        packageName: StrictStr,
        version: Annotated[Optional[StrictStr], Field(description="Specific package version to retrieve. Defaults to the latest available version.")],
    ) -> PackageDetail:
        ...


    async def get_published_package_registry(
        self,
        packageName: StrictStr,
    ) -> PublishedPackageRegistry:
        ...


    async def download_published_package(
        self,
        packageName: StrictStr,
        version: Annotated[Optional[StrictStr], Field(description="Specific package version to retrieve. Defaults to the latest available version.")],
    ) -> Any:
        ...


    async def reserve_published_package(
        self,
        packageName: StrictStr,
        published_package_reserve_request: Optional[PublishedPackageReserveRequest],
    ) -> PublishedPackageRegistry:
        ...


    async def set_published_package_version_status(
        self,
        packageName: StrictStr,
        version: StrictStr,
        published_package_status_request: PublishedPackageStatusRequest,
    ) -> PackageDetail:
        ...


    async def set_published_package_tag(
        self,
        packageName: StrictStr,
        tag: StrictStr,
        published_package_tag_request: PublishedPackageTagRequest,
    ) -> None:
        ...


    async def delete_published_package_tag(
        self,
        packageName: StrictStr,
        tag: StrictStr,
    ) -> None:
        ...


    async def update_published_package_visibility(
        self,
        packageName: StrictStr,
        published_package_visibility_request: PublishedPackageVisibilityRequest,
    ) -> PublishedPackageRegistry:
        ...


    async def transfer_published_package(
        self,
        packageName: StrictStr,
        published_package_transfer_request: PublishedPackageTransferRequest,
    ) -> PublishedPackageRegistry:
        ...
