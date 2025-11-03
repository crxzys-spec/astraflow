# coding: utf-8

from typing import ClassVar, Dict, List, Tuple  # noqa: F401

from pydantic import Field, StrictStr
from typing import Optional
from typing_extensions import Annotated
from scheduler_api.security_api import get_token_bearerAuth

class BaseEventsApi:
    subclasses: ClassVar[Tuple] = ()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        BaseEventsApi.subclasses = BaseEventsApi.subclasses + (cls,)
    async def sse_global_events(
        self,
        client_session_id: Annotated[StrictStr, Field(description="Frontend-generated session identifier (UUID) used to route SSE events.")],
        last_event_id: Annotated[Optional[StrictStr], Field(description="Resume SSE from a specific monotonic event id")],
    ) -> str:
        ...
