from __future__ import annotations

from typing import Optional

from scheduler_api.apis.audit_api_base import BaseAuditApi
from scheduler_api.auth.roles import AUDIT_VIEW_ROLES, require_roles
from scheduler_api.models.list_audit_events200_response import ListAuditEvents200Response
from scheduler_api.service.audit import AuditService

_audit_service = AuditService()


class AuditApiImpl(BaseAuditApi):
    async def list_audit_events(
        self,
        limit: Optional[int],
        cursor: Optional[str],
        action: Optional[str],
        actor_id: Optional[str],
        target_type: Optional[str],
    ) -> ListAuditEvents200Response:
        require_roles(*AUDIT_VIEW_ROLES)
        items, next_cursor = _audit_service.list_events(
            limit=limit,
            cursor=cursor,
            action=action,
            actor_id=actor_id,
            target_type=target_type,
        )
        return ListAuditEvents200Response(items=items, nextCursor=next_cursor)
