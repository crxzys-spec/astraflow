# coding: utf-8

from typing import ClassVar, Dict, List, Tuple, Any  # noqa: F401
from fastapi import UploadFile

from pydantic import Field, StrictBytes, StrictStr
from typing import List, Optional, Tuple, Union
from typing_extensions import Annotated
from scheduler_api.models.error import Error
from scheduler_api.models.hub_package_detail import HubPackageDetail
from scheduler_api.models.hub_package_install_request import HubPackageInstallRequest
from scheduler_api.models.hub_package_install_response import HubPackageInstallResponse
from scheduler_api.models.hub_package_list_response import HubPackageListResponse
from scheduler_api.models.hub_package_version_detail import HubPackageVersionDetail
from scheduler_api.models.hub_visibility import HubVisibility
from scheduler_api.security_api import get_token_bearerAuth

class BaseHubPackagesApi:
    subclasses: ClassVar[Tuple] = ()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        BaseHubPackagesApi.subclasses = BaseHubPackagesApi.subclasses + (cls,)
    async def list_hub_packages(
        self,
        q: Annotated[Optional[StrictStr], Field(description="Search query")],
        tag: Annotated[Optional[StrictStr], Field(description="Filter by tag")],
        owner: Annotated[Optional[StrictStr], Field(description="Filter by owner id")],
        page: Annotated[Optional[Annotated[int, Field(ge=1)]], Field(description="1-based page index")],
        page_size: Annotated[Optional[Annotated[int, Field(le=200, ge=1)]], Field(description="Page size")],
    ) -> HubPackageListResponse:
        ...


    async def publish_hub_package(
        self,
        file: UploadFile,
        visibility: Optional[HubVisibility],
        summary: Optional[StrictStr],
        readme: Optional[StrictStr],
        tags: Optional[List[StrictStr]],
    ) -> HubPackageVersionDetail:
        ...


    async def get_hub_package(
        self,
        packageName: StrictStr,
    ) -> HubPackageDetail:
        ...


    async def get_hub_package_version(
        self,
        packageName: StrictStr,
        version: StrictStr,
    ) -> HubPackageVersionDetail:
        ...


    async def download_hub_package_archive(
        self,
        packageName: StrictStr,
        version: Annotated[Optional[StrictStr], Field(description="Optional version to download")],
    ) -> Any:
        ...


    async def install_hub_package(
        self,
        packageName: StrictStr,
        hub_package_install_request: Optional[HubPackageInstallRequest],
    ) -> HubPackageInstallResponse:
        ...
