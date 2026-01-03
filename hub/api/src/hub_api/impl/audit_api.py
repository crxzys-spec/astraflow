from __future__ import annotations

from hub_api.apis.audit_api_base import BaseAuditApi
from hub_api.models.audit_event_list import AuditEventList
from hub_api.services.audit_service import AuditService

_service = AuditService()


class AuditApiImpl(BaseAuditApi):
    async def list_audit_events(
        self,
        actor: str | None,
        action: str | None,
        limit: int | None,
    ) -> AuditEventList:
        return await _service.list_audit_events(actor, action, limit)
