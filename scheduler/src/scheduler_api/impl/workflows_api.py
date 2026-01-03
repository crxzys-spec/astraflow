from __future__ import annotations

from typing import Optional

from scheduler_api.http.errors import bad_request, forbidden, internal_error, not_found

from scheduler_api.auth.roles import WORKFLOW_EDIT_ROLES, WORKFLOW_VIEW_ROLES, require_roles
from scheduler_api.apis.workflows_api_base import BaseWorkflowsApi
from scheduler_api.models.list_workflows200_response_items_inner import (
    ListWorkflows200ResponseItemsInner,
)
from scheduler_api.models.persist_workflow201_response import PersistWorkflow201Response
from scheduler_api.models.workflow_list import WorkflowList
from scheduler_api.models.workflow_preview import WorkflowPreview
from scheduler_api.service.workflows import (
    WorkflowCorruptedError,
    WorkflowNotFoundError,
    WorkflowPermissionError,
    WorkflowService,
    WorkflowValidationError,
)

_workflow_service = WorkflowService()


class WorkflowsApiImpl(BaseWorkflowsApi):
    async def list_workflows(
        self,
        limit: Optional[int],
        cursor: Optional[str],
    ) -> WorkflowList:
        del cursor  # pagination cursor reserved for future implementation
        token = require_roles(*WORKFLOW_VIEW_ROLES)
        page_size = limit or 50
        is_admin = "admin" in (token.roles if token else [])
        owner_id = token.sub if token else None
        items = _workflow_service.list_workflows(
            limit=page_size,
            owner_id=owner_id,
            is_admin=is_admin,
        )
        return WorkflowList(items=items, next_cursor=None)

    async def persist_workflow(
        self,
        list_workflows200_response_items_inner: ListWorkflows200ResponseItemsInner,
        idempotency_key: Optional[str],
    ) -> PersistWorkflow201Response:
        del idempotency_key  # reserved for future enhancement
        token = require_roles(*WORKFLOW_EDIT_ROLES)
        try:
            return _workflow_service.persist_workflow(
                list_workflows200_response_items_inner,
                actor_id=token.sub if token else None,
            )
        except WorkflowValidationError as exc:
            raise bad_request(exc.message, error=exc.error) from exc
        except WorkflowPermissionError as exc:
            raise forbidden(str(exc)) from exc

    async def get_workflow(
        self,
        workflowId: str,
    ) -> Workflow1:
        token = require_roles(*WORKFLOW_VIEW_ROLES)
        is_admin = "admin" in (token.roles if token else [])
        owner_id = token.sub if token else None
        try:
            return _workflow_service.get_workflow(
                workflowId,
                owner_id=owner_id,
                is_admin=is_admin,
            )
        except WorkflowNotFoundError as exc:
            raise not_found(str(exc), error="workflow_not_found") from exc
        except WorkflowPermissionError as exc:
            raise forbidden(str(exc)) from exc
        except WorkflowCorruptedError as exc:
            raise internal_error(str(exc), error="workflow_corrupted") from exc

    async def delete_workflow(
        self,
        workflowId: str,
    ) -> None:
        token = require_roles(*WORKFLOW_EDIT_ROLES)
        is_admin = "admin" in (token.roles if token else [])
        owner_id = token.sub if token else None
        try:
            _workflow_service.delete_workflow(
                workflowId,
                owner_id=owner_id,
                is_admin=is_admin,
                actor_id=token.sub if token else None,
            )
        except WorkflowNotFoundError as exc:
            raise not_found(str(exc), error="workflow_not_found") from exc
        except WorkflowPermissionError as exc:
            raise forbidden(str(exc)) from exc

    async def get_workflow_preview(self, workflowId: str) -> WorkflowPreview:
        require_roles(*WORKFLOW_VIEW_ROLES)
        try:
            preview_image = _workflow_service.get_workflow_preview(workflowId)
        except WorkflowNotFoundError as exc:
            raise not_found("Workflow not found", error="workflow_not_found") from exc
        return WorkflowPreview(preview_image=preview_image)

    async def set_workflow_preview(self, workflowId: str, payload: WorkflowPreview) -> WorkflowPreview:
        token = require_roles(*WORKFLOW_EDIT_ROLES)
        preview_value = None
        if payload and isinstance(payload.preview_image, str):
            preview_value = payload.preview_image
        try:
            preview_image = _workflow_service.set_workflow_preview(
                workflowId,
                preview_image=preview_value,
                actor_id=token.sub if token else None,
            )
        except WorkflowNotFoundError as exc:
            raise not_found("Workflow not found", error="workflow_not_found") from exc
        return WorkflowPreview(preview_image=preview_image)
