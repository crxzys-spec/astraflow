# coding: utf-8

from typing import ClassVar, Dict, List, Tuple  # noqa: F401

from pydantic import Field, StrictStr
from typing import Optional
from typing_extensions import Annotated
from hub_api.models.error import Error
from hub_api.models.hub_workflow_detail import HubWorkflowDetail
from hub_api.models.workflow_definition import WorkflowDefinition
from hub_api.models.workflow_list_response import WorkflowListResponse
from hub_api.models.workflow_publish_request import WorkflowPublishRequest
from hub_api.models.workflow_publish_response import WorkflowPublishResponse
from hub_api.models.workflow_version_detail import WorkflowVersionDetail
from hub_api.models.workflow_version_list import WorkflowVersionList
from hub_api.security_api import get_token_bearerAuth

class BaseWorkflowsApi:
    subclasses: ClassVar[Tuple] = ()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        BaseWorkflowsApi.subclasses = BaseWorkflowsApi.subclasses + (cls,)
    async def list_workflows(
        self,
        q: Annotated[Optional[StrictStr], Field(description="Search query")],
        tag: Annotated[Optional[StrictStr], Field(description="Filter by tag")],
        owner: Annotated[Optional[StrictStr], Field(description="Filter by owner id")],
        page: Annotated[Optional[Annotated[int, Field(ge=1)]], Field(description="1-based page index")],
        page_size: Annotated[Optional[Annotated[int, Field(le=200, ge=1)]], Field(description="Page size")],
    ) -> WorkflowListResponse:
        ...


    async def publish_workflow(
        self,
        workflow_publish_request: WorkflowPublishRequest,
    ) -> WorkflowPublishResponse:
        ...


    async def get_workflow(
        self,
        workflowId: StrictStr,
    ) -> HubWorkflowDetail:
        ...


    async def list_workflow_versions(
        self,
        workflowId: StrictStr,
        page: Annotated[Optional[Annotated[int, Field(ge=1)]], Field(description="1-based page index")],
        page_size: Annotated[Optional[Annotated[int, Field(le=200, ge=1)]], Field(description="Page size")],
    ) -> WorkflowVersionList:
        ...


    async def get_workflow_version(
        self,
        workflowId: StrictStr,
        versionId: StrictStr,
    ) -> WorkflowVersionDetail:
        ...


    async def get_workflow_definition(
        self,
        workflowId: StrictStr,
        versionId: StrictStr,
    ) -> WorkflowDefinition:
        ...
