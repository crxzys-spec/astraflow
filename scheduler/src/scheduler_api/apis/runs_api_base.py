# coding: utf-8

from typing import ClassVar, Dict, List, Tuple  # noqa: F401

from pydantic import Field, StrictStr, field_validator
from typing import Optional
from typing_extensions import Annotated
from scheduler_api.models.auth_login401_response import AuthLogin401Response
from scheduler_api.models.list_runs200_response import ListRuns200Response
from scheduler_api.models.list_runs200_response_items_inner import ListRuns200ResponseItemsInner
from scheduler_api.models.start_run202_response import StartRun202Response
from scheduler_api.models.start_run_request import StartRunRequest
from scheduler_api.models.start_run_request_workflow import StartRunRequestWorkflow
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
        status: Optional[StrictStr],
        client_id: Optional[StrictStr],
    ) -> ListRuns200Response:
        ...


    async def start_run(
        self,
        start_run_request: StartRunRequest,
        idempotency_key: Annotated[Optional[Annotated[str, Field(strict=True, max_length=64)]], Field(description="Optional idempotency key for safe retries; if reused with a different body, return 409")],
    ) -> StartRun202Response:
        ...


    async def get_run(
        self,
        runId: StrictStr,
    ) -> ListRuns200ResponseItemsInner:
        ...


    async def get_run_definition(
        self,
        runId: StrictStr,
    ) -> StartRunRequestWorkflow:
        ...
