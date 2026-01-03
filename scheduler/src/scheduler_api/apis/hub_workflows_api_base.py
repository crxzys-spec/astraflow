# coding: utf-8

from typing import ClassVar, Dict, List, Tuple, Any  # noqa: F401

from pydantic import Field, StrictStr
from typing import Any, Dict, Optional
from typing_extensions import Annotated
from scheduler_api.models.error import Error
from scheduler_api.models.hub_workflow_detail import HubWorkflowDetail
from scheduler_api.models.hub_workflow_import_request import HubWorkflowImportRequest
from scheduler_api.models.hub_workflow_import_response import HubWorkflowImportResponse
from scheduler_api.models.hub_workflow_list_response import HubWorkflowListResponse
from scheduler_api.models.hub_workflow_publish_request import HubWorkflowPublishRequest
from scheduler_api.models.hub_workflow_publish_response import HubWorkflowPublishResponse
from scheduler_api.models.hub_workflow_version_detail import HubWorkflowVersionDetail
from scheduler_api.models.hub_workflow_version_list import HubWorkflowVersionList
from scheduler_api.security_api import get_token_bearerAuth

class BaseHubWorkflowsApi:
    subclasses: ClassVar[Tuple] = ()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        BaseHubWorkflowsApi.subclasses = BaseHubWorkflowsApi.subclasses + (cls,)
    async def list_hub_workflows(
        self,
        q: Annotated[Optional[StrictStr], Field(description="Search query")],
        tag: Annotated[Optional[StrictStr], Field(description="Filter by tag")],
        owner: Annotated[Optional[StrictStr], Field(description="Filter by owner id")],
        page: Annotated[Optional[Annotated[int, Field(ge=1)]], Field(description="1-based page index")],
        page_size: Annotated[Optional[Annotated[int, Field(le=200, ge=1)]], Field(description="Page size")],
    ) -> HubWorkflowListResponse:
        ...


    async def publish_hub_workflow(
        self,
        hub_workflow_publish_request: HubWorkflowPublishRequest,
    ) -> HubWorkflowPublishResponse:
        ...


    async def get_hub_workflow(
        self,
        workflowId: StrictStr,
    ) -> HubWorkflowDetail:
        ...


    async def list_hub_workflow_versions(
        self,
        workflowId: StrictStr,
    ) -> HubWorkflowVersionList:
        ...


    async def get_hub_workflow_version(
        self,
        workflowId: StrictStr,
        versionId: StrictStr,
    ) -> HubWorkflowVersionDetail:
        ...


    async def get_hub_workflow_definition(
        self,
        workflowId: StrictStr,
        versionId: StrictStr,
    ) -> Dict[str, object]:
        ...


    async def import_hub_workflow(
        self,
        workflowId: StrictStr,
        hub_workflow_import_request: Optional[HubWorkflowImportRequest],
    ) -> HubWorkflowImportResponse:
        ...
