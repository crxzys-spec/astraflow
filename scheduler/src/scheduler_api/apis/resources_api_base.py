# coding: utf-8

from typing import ClassVar, Dict, List, Tuple  # noqa: F401
from fastapi import UploadFile

from pydantic import Field, StrictBytes, StrictStr
from typing import Any, Tuple, Union
from typing_extensions import Annotated
from scheduler_api.models.error import Error
from scheduler_api.models.resource import Resource
from scheduler_api.models.resource_upload_init_request import ResourceUploadInitRequest
from scheduler_api.models.resource_upload_part import ResourceUploadPart
from scheduler_api.models.resource_upload_session import ResourceUploadSession
from scheduler_api.security_api import get_token_bearerAuth

class BaseResourcesApi:
    subclasses: ClassVar[Tuple] = ()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        BaseResourcesApi.subclasses = BaseResourcesApi.subclasses + (cls,)
    async def upload_resource(
        self,
        file: UploadFile,
    ) -> Resource:
        ...


    async def create_resource_upload(
        self,
        resource_upload_init_request: ResourceUploadInitRequest,
    ) -> ResourceUploadSession:
        ...


    async def get_resource_upload(
        self,
        uploadId: StrictStr,
    ) -> ResourceUploadSession:
        ...


    async def delete_resource_upload(
        self,
        uploadId: StrictStr,
    ) -> None:
        ...


    async def upload_resource_part(
        self,
        uploadId: StrictStr,
        partNumber: Annotated[int, Field(ge=0)],
        file: UploadFile,
    ) -> ResourceUploadPart:
        ...


    async def complete_resource_upload(
        self,
        uploadId: StrictStr,
    ) -> Resource:
        ...


    async def get_resource(
        self,
        resourceId: StrictStr,
    ) -> Resource:
        ...


    async def delete_resource(
        self,
        resourceId: StrictStr,
    ) -> None:
        ...


    async def download_resource(
        self,
        resourceId: StrictStr,
    ) -> Any:
        ...
