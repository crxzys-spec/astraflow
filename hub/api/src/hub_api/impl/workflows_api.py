from __future__ import annotations

from hub_api.apis.workflows_api_base import BaseWorkflowsApi
from hub_api.models.hub_workflow_detail import HubWorkflowDetail
from hub_api.models.workflow_list_response import WorkflowListResponse
from hub_api.models.workflow_publish_request import WorkflowPublishRequest
from hub_api.models.workflow_publish_response import WorkflowPublishResponse
from hub_api.models.workflow_version_detail import WorkflowVersionDetail
from hub_api.models.workflow_version_list import WorkflowVersionList
from hub_api.services.workflows_service import WorkflowsService

_service = WorkflowsService()


class WorkflowsApiImpl(BaseWorkflowsApi):
    async def list_workflows(
        self,
        q: str | None,
        tag: str | None,
        owner: str | None,
        page: int | None,
        page_size: int | None,
    ) -> WorkflowListResponse:
        return await _service.list_workflows(q, tag, owner, page, page_size)

    async def publish_workflow(
        self,
        workflow_publish_request: WorkflowPublishRequest,
    ) -> WorkflowPublishResponse:
        return await _service.publish_workflow(workflow_publish_request)

    async def get_workflow(
        self,
        workflowId: str,
    ) -> HubWorkflowDetail:
        return await _service.get_workflow(workflowId)

    async def list_workflow_versions(
        self,
        workflowId: str,
        page: int | None,
        page_size: int | None,
    ) -> WorkflowVersionList:
        return await _service.list_workflow_versions(workflowId, page, page_size)

    async def get_workflow_version(
        self,
        workflowId: str,
        versionId: str,
    ) -> WorkflowVersionDetail:
        return await _service.get_workflow_version(workflowId, versionId)

    async def get_workflow_definition(
        self,
        workflowId: str,
        versionId: str,
    ) -> dict[str, object]:
        return await _service.get_workflow_definition(workflowId, versionId)
