# coding: utf-8

from typing import ClassVar, Dict, List, Tuple  # noqa: F401

from pydantic import Field, StrictStr
from typing import Any, Optional
from typing_extensions import Annotated
from scheduler_api.models.auth_login401_response import AuthLogin401Response
from scheduler_api.models.list_workflows200_response import ListWorkflows200Response
from scheduler_api.models.list_workflows200_response_items_inner import ListWorkflows200ResponseItemsInner
from scheduler_api.models.persist_workflow201_response import PersistWorkflow201Response
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
    ) -> ListWorkflows200Response:
        ...


    async def persist_workflow(
        self,
        list_workflows200_response_items_inner: ListWorkflows200ResponseItemsInner,
        idempotency_key: Annotated[Optional[Annotated[str, Field(strict=True, max_length=64)]], Field(description="Optional idempotency key for safe retries; if reused with a different body, return 409")],
    ) -> PersistWorkflow201Response:
        ...


    async def get_workflow(
        self,
        workflowId: StrictStr,
    ) -> ListWorkflows200ResponseItemsInner:
        ...


    async def delete_workflow(
        self,
        workflowId: StrictStr,
    ) -> None:
        """Marks the workflow record as deleted so it is hidden from listings and future reads."""
        ...
