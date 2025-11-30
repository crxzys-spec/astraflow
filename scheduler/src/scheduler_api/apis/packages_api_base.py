# coding: utf-8

from typing import ClassVar, Dict, List, Tuple  # noqa: F401

from pydantic import Field, StrictStr
from typing import Optional
from typing_extensions import Annotated
from scheduler_api.models.error import Error
from scheduler_api.models.package_detail import PackageDetail
from scheduler_api.models.package_list import PackageList
from scheduler_api.security_api import get_token_bearerAuth

class BasePackagesApi:
    subclasses: ClassVar[Tuple] = ()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        BasePackagesApi.subclasses = BasePackagesApi.subclasses + (cls,)
    async def list_packages(
        self,
    ) -> PackageList:
        ...


    async def get_package(
        self,
        packageName: StrictStr,
        version: Annotated[Optional[StrictStr], Field(description="Specific package version to retrieve. Defaults to the latest available version.")],
    ) -> PackageDetail:
        ...
