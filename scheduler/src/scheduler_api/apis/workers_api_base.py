# coding: utf-8

from typing import ClassVar, Dict, List, Tuple  # noqa: F401

from pydantic import Field, StrictStr
from typing import Optional
from typing_extensions import Annotated
from scheduler_api.models.auth_login401_response import AuthLogin401Response
from scheduler_api.models.list_workers200_response import ListWorkers200Response
from scheduler_api.models.list_workers200_response_items_inner import ListWorkers200ResponseItemsInner
from scheduler_api.models.send_worker_command202_response import SendWorkerCommand202Response
from scheduler_api.models.send_worker_command_request import SendWorkerCommandRequest
from scheduler_api.security_api import get_token_bearerAuth

class BaseWorkersApi:
    subclasses: ClassVar[Tuple] = ()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        BaseWorkersApi.subclasses = BaseWorkersApi.subclasses + (cls,)
    async def list_workers(
        self,
        queue: Optional[StrictStr],
        limit: Optional[Annotated[int, Field(le=200, strict=True, ge=1)]],
        cursor: Optional[StrictStr],
    ) -> ListWorkers200Response:
        ...


    async def get_worker(
        self,
        workerId: StrictStr,
    ) -> ListWorkers200ResponseItemsInner:
        ...


    async def send_worker_command(
        self,
        workerId: StrictStr,
        send_worker_command_request: SendWorkerCommandRequest,
        idempotency_key: Annotated[Optional[Annotated[str, Field(strict=True, max_length=64)]], Field(description="Optional idempotency key for safe retries; if reused with a different body, return 409")],
    ) -> SendWorkerCommand202Response:
        ...
