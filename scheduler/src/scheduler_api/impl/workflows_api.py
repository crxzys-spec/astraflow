from __future__ import annotations

from typing import Optional

from scheduler_api.apis.workflows_api_base import BaseWorkflowsApi
from scheduler_api.models.list_workflows200_response import ListWorkflows200Response
from scheduler_api.models.list_workflows200_response_items_inner import (
    ListWorkflows200ResponseItemsInner,
)
from scheduler_api.models.persist_workflow201_response import PersistWorkflow201Response


class WorkflowsApiImpl(BaseWorkflowsApi):
    async def list_workflows(
        self,
        limit: Optional[int],
        cursor: Optional[str],
    ) -> ListWorkflows200Response:
        raise NotImplementedError

    async def persist_workflow(
        self,
        list_workflows200_response_items_inner: ListWorkflows200ResponseItemsInner,
        idempotency_key: Optional[str],
    ) -> PersistWorkflow201Response:
        raise NotImplementedError

    async def get_workflow(
        self,
        workflowId: str,
    ) -> ListWorkflows200ResponseItemsInner:
        raise NotImplementedError
