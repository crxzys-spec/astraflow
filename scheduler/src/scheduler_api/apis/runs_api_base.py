# coding: utf-8

from typing import ClassVar, Dict, List, Tuple  # noqa: F401

from pydantic import Field, StrictStr
from typing import Optional
from typing_extensions import Annotated
from scheduler_api.models.error import Error
from scheduler_api.models.run1 import Run1
from scheduler_api.models.run_list1 import RunList1
from scheduler_api.models.run_ref1 import RunRef1
from scheduler_api.models.run_start_request1 import RunStartRequest1
from scheduler_api.models.run_status import RunStatus
from scheduler_api.models.workflow1 import Workflow1
from scheduler_api.security_api import get_token_bearerAuth

class BaseRunsApi:
    subclasses: ClassVar[Tuple] = ()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        BaseRunsApi.subclasses = BaseRunsApi.subclasses + (cls,)
    async def list_runs(
        self,
        limit: Optional[Annotated[int, Field(le=200, ge=1)]],
        cursor: Optional[StrictStr],
        status: Optional[RunStatus],
        client_id: Optional[StrictStr],
    ) -> RunList1:
        ...


    async def start_run(
        self,
        run_start_request1: RunStartRequest1,
        idempotency_key: Annotated[Optional[Annotated[str, Field(strict=True, max_length=64)]], Field(description="Optional idempotency key for safe retries; if reused with a different body, return 409")],
    ) -> RunRef1:
        ...


    async def get_run(
        self,
        runId: StrictStr,
    ) -> Run1:
        ...


    async def cancel_run(
        self,
        runId: StrictStr,
    ) -> RunRef1:
        ...


    async def get_run_definition(
        self,
        runId: StrictStr,
    ) -> Workflow1:
        ...
