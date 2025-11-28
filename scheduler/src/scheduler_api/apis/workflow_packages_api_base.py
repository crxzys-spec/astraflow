# coding: utf-8

from typing import ClassVar, Dict, List, Tuple  # noqa: F401

from pydantic import Field, StrictStr
from typing import Any, Optional
from typing_extensions import Annotated
from scheduler_api.models.error import Error
from scheduler_api.models.workflow_package_clone_request import WorkflowPackageCloneRequest
from scheduler_api.models.workflow_package_detail1 import WorkflowPackageDetail1
from scheduler_api.models.workflow_package_list1 import WorkflowPackageList1
from scheduler_api.models.workflow_package_version_list1 import WorkflowPackageVersionList1
from scheduler_api.models.workflow_publish_request import WorkflowPublishRequest
from scheduler_api.models.workflow_publish_response import WorkflowPublishResponse
from scheduler_api.models.workflow_ref import WorkflowRef
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
    ) -> WorkflowPackageList1:
        ...


    async def get_workflow_package(
        self,
        packageId: StrictStr,
    ) -> WorkflowPackageDetail1:
        ...


    async def delete_workflow_package(
        self,
        packageId: StrictStr,
    ) -> None:
        ...


    async def list_workflow_package_versions(
        self,
        packageId: StrictStr,
    ) -> WorkflowPackageVersionList1:
        ...


    async def clone_workflow_package(
        self,
        packageId: StrictStr,
        workflow_package_clone_request: Optional[WorkflowPackageCloneRequest],
    ) -> WorkflowRef:
        ...


    async def publish_workflow(
        self,
        workflowId: StrictStr,
        workflow_publish_request: WorkflowPublishRequest,
    ) -> WorkflowPublishResponse:
        ...
