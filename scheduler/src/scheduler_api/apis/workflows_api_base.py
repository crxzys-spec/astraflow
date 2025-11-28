# coding: utf-8

from typing import ClassVar, Dict, List, Tuple  # noqa: F401

from pydantic import Field, StrictStr
from typing import Any, Optional
from typing_extensions import Annotated
from scheduler_api.models.error import Error
from scheduler_api.models.workflow1 import Workflow1
from scheduler_api.models.workflow_list1 import WorkflowList1
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
    ) -> WorkflowList1:
        ...


    async def persist_workflow(
        self,
        workflow1: Workflow1,
        idempotency_key: Annotated[Optional[Annotated[str, Field(strict=True, max_length=64)]], Field(description="Optional idempotency key for safe retries; if reused with a different body, return 409")],
    ) -> WorkflowRef:
        ...


    async def get_workflow(
        self,
        workflowId: StrictStr,
    ) -> Workflow1:
        ...


    async def delete_workflow(
        self,
        workflowId: StrictStr,
    ) -> None:
        """Marks the workflow record as deleted so it is hidden from listings and future reads."""
        ...
