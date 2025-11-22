# coding: utf-8

from typing import ClassVar, Dict, List, Tuple  # noqa: F401

from pydantic import Field, StrictStr
from typing import Any, Optional
from typing_extensions import Annotated
from scheduler_api.models.auth_login401_response import AuthLogin401Response
from scheduler_api.models.clone_workflow_package_request import CloneWorkflowPackageRequest
from scheduler_api.models.get_workflow_package200_response import GetWorkflowPackage200Response
from scheduler_api.models.list_workflow_package_versions200_response import ListWorkflowPackageVersions200Response
from scheduler_api.models.list_workflow_packages200_response import ListWorkflowPackages200Response
from scheduler_api.models.persist_workflow201_response import PersistWorkflow201Response
from scheduler_api.models.publish_workflow200_response import PublishWorkflow200Response
from scheduler_api.models.publish_workflow_request import PublishWorkflowRequest
from scheduler_api.security_api import get_token_bearerAuth

class BaseWorkflowPackagesApi:
    subclasses: ClassVar[Tuple] = ()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        BaseWorkflowPackagesApi.subclasses = BaseWorkflowPackagesApi.subclasses + (cls,)
    async def list_workflow_packages(
        self,
        limit: Optional[Annotated[int, Field(le=200, ge=1)]],
        cursor: Optional[StrictStr],
        owner: Annotated[Optional[StrictStr], Field(description="Filter by owner id; use `me` for the caller's id.")],
        visibility: Annotated[Optional[StrictStr], Field(description="Filter by visibility (private, internal, public).")],
        search: Annotated[Optional[StrictStr], Field(description="Full-text search across slug, display name, and summary.")],
    ) -> ListWorkflowPackages200Response:
        ...


    async def get_workflow_package(
        self,
        packageId: StrictStr,
    ) -> GetWorkflowPackage200Response:
        ...


    async def delete_workflow_package(
        self,
        packageId: StrictStr,
    ) -> None:
        ...


    async def list_workflow_package_versions(
        self,
        packageId: StrictStr,
    ) -> ListWorkflowPackageVersions200Response:
        ...


    async def clone_workflow_package(
        self,
        packageId: StrictStr,
        clone_workflow_package_request: Optional[CloneWorkflowPackageRequest],
    ) -> PersistWorkflow201Response:
        ...


    async def publish_workflow(
        self,
        workflowId: StrictStr,
        publish_workflow_request: PublishWorkflowRequest,
    ) -> PublishWorkflow200Response:
        ...
