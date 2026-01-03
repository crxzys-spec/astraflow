from __future__ import annotations

from fastapi import HTTPException, status

from hub_api.repo.audit import list_audit_events
from hub_api.models.audit_event import AuditEvent
from hub_api.models.audit_event_list import AuditEventList
from hub_api.security_api import is_admin, require_actor


class AuditService:
    async def list_audit_events(
        self,
        actor: str | None,
        action: str | None,
        limit: int | None,
    ) -> AuditEventList:
        actor_id = require_actor()
        admin = is_admin()
        if actor and actor != actor_id and not admin:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        events = list_audit_events(
            actor_id=actor_id,
            action=action,
            limit=limit,
            is_admin=admin,
        )
        if actor and admin:
            events = [event for event in events if event.get("actorId") == actor]
        items = [AuditEvent.from_dict(event) for event in events]
        return AuditEventList(items=items)
