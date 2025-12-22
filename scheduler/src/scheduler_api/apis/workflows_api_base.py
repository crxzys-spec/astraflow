# coding: utf-8

from typing import ClassVar, Dict, List, Tuple  # noqa: F401

from pydantic import Field, StrictStr
from typing import Any, Optional
from typing_extensions import Annotated
from scheduler_api.models.error import Error
from scheduler_api.models.workflow import Workflow
from scheduler_api.models.workflow_list import WorkflowList
from scheduler_api.models.workflow_preview import WorkflowPreview
from scheduler_api.models.workflow_ref import WorkflowRef
from scheduler_api.security_api import get_token_bearerAuth

class BaseWorkflowsApi:
    subclasses: ClassVar[Tuple] = ()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        BaseWorkflowsApi.subclasses = BaseWorkflowsApi.subclasses + (cls,)
    async def list_workflows(
        self,
        limit: Optional[Annotated[int, Field(le=200, ge=1)]],
        cursor: Optional[StrictStr],
    ) -> WorkflowList:
        ...


    async def persist_workflow(
        self,
        workflow: Workflow,
        idempotency_key: Annotated[Optional[Annotated[str, Field(max_length=64)]], Field(description="Optional idempotency key for safe retries; if reused with a different body, return 409")],
    ) -> WorkflowRef:
        ...


    async def get_workflow(
        self,
        workflowId: StrictStr,
    ) -> Workflow:
        ...


    async def delete_workflow(
        self,
        workflowId: StrictStr,
    ) -> None:
        """Marks the workflow record as deleted so it is hidden from listings and future reads."""
        ...


    async def get_workflow_preview(
        self,
        workflowId: StrictStr,
    ) -> WorkflowPreview:
        ...


    async def set_workflow_preview(
        self,
        workflowId: StrictStr,
        workflow_preview: WorkflowPreview,
    ) -> WorkflowPreview:
        ...
