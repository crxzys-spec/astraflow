# coding: utf-8

from typing import ClassVar, Dict, List, Tuple  # noqa: F401

from pydantic import Field, StrictStr
from typing import Optional
from typing_extensions import Annotated
from scheduler_api.models.list_audit_events200_response import ListAuditEvents200Response
from scheduler_api.security_api import get_token_bearerAuth

class BaseAuditApi:
    subclasses: ClassVar[Tuple] = ()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        BaseAuditApi.subclasses = BaseAuditApi.subclasses + (cls,)
    async def list_audit_events(
        self,
        limit: Optional[Annotated[int, Field(le=200, strict=True, ge=1)]],
        cursor: Annotated[Optional[StrictStr], Field(description="Reserved for future pagination")],
        action: Annotated[Optional[StrictStr], Field(description="Filter by action name")],
        actor_id: Annotated[Optional[StrictStr], Field(description="Filter by actor id")],
        target_type: Annotated[Optional[StrictStr], Field(description="Filter by target type")],
    ) -> ListAuditEvents200Response:
        ...
