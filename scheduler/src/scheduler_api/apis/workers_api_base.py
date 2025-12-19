# coding: utf-8

from typing import ClassVar, Dict, List, Tuple  # noqa: F401

from pydantic import Field, StrictStr
from typing import Optional
from typing_extensions import Annotated
from scheduler_api.models.command_ref import CommandRef
from scheduler_api.models.error import Error
from scheduler_api.models.list_workers200_response import ListWorkers200Response
from scheduler_api.models.worker import Worker
from scheduler_api.models.worker_command import WorkerCommand
from scheduler_api.security_api import get_token_bearerAuth

class BaseWorkersApi:
    subclasses: ClassVar[Tuple] = ()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        BaseWorkersApi.subclasses = BaseWorkersApi.subclasses + (cls,)
    async def list_workers(
        self,
        queue: Optional[StrictStr],
        limit: Optional[Annotated[int, Field(le=200, ge=1)]],
        cursor: Optional[StrictStr],
    ) -> ListWorkers200Response:
        ...


    async def get_worker(
        self,
        workerName: StrictStr,
    ) -> Worker:
        ...


    async def send_worker_command(
        self,
        workerName: StrictStr,
        worker_command: WorkerCommand,
        idempotency_key: Annotated[Optional[Annotated[str, Field(strict=True, max_length=64)]], Field(description="Optional idempotency key for safe retries; if reused with a different body, return 409")],
    ) -> CommandRef:
        ...
