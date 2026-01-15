from __future__ import annotations

from hub_api.apis.workflows_api_base import BaseWorkflowsApi
from hub_api.models.hub_workflow_detail import HubWorkflowDetail
from hub_api.models.workflow_permission import WorkflowPermission
from hub_api.models.workflow_permission_create_request import WorkflowPermissionCreateRequest
from hub_api.models.workflow_permission_list import WorkflowPermissionList
from hub_api.models.workflow_permission_update_request import WorkflowPermissionUpdateRequest
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

    async def list_workflow_permissions(
        self,
        workflowId: str,
    ) -> WorkflowPermissionList:
        return await _service.list_workflow_permissions(workflowId)

    async def add_workflow_permission(
        self,
        workflowId: str,
        workflow_permission_create_request: WorkflowPermissionCreateRequest,
    ) -> WorkflowPermission:
        return await _service.add_workflow_permission(workflowId, workflow_permission_create_request)

    async def delete_workflow_permission(
        self,
        workflowId: str,
        permissionId: str,
    ) -> None:
        return await _service.delete_workflow_permission(workflowId, permissionId)

    async def update_workflow_permission(
        self,
        workflowId: str,
        permissionId: str,
        workflow_permission_update_request: WorkflowPermissionUpdateRequest,
    ) -> WorkflowPermission:
        return await _service.update_workflow_permission(
            workflowId,
            permissionId,
            workflow_permission_update_request,
        )
