# coding: utf-8

from typing import ClassVar, Dict, List, Tuple  # noqa: F401

from pydantic import Field, StrictStr
from typing import Optional
from typing_extensions import Annotated
from hub_api.models.audit_event_list import AuditEventList
from hub_api.models.error import Error
from hub_api.security_api import get_token_bearerAuth

class BaseAuditApi:
    subclasses: ClassVar[Tuple] = ()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        BaseAuditApi.subclasses = BaseAuditApi.subclasses + (cls,)
    async def list_audit_events(
        self,
        actor: Annotated[Optional[StrictStr], Field(description="Filter by actor id")],
        action: Annotated[Optional[StrictStr], Field(description="Filter by action")],
        limit: Annotated[Optional[Annotated[int, Field(le=200, ge=1)]], Field(description="Max events to return")],
    ) -> AuditEventList:
        ...
