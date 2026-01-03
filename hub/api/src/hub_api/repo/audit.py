from __future__ import annotations

from typing import Any

from sqlalchemy import select

from hub_api.db.models import HubAuditEvent
from hub_api.db.session import SessionLocal
from hub_api.repo.common import _generate_id, _now

def record_audit_event(
    *,
    action: str,
    actor_id: str,
    target_type: str | None,
    target_id: str | None,
    metadata: dict[str, Any] | None = None,
) -> None:
    event_id = _generate_id()
    with SessionLocal() as session:
        session.add(
            HubAuditEvent(
                id=event_id,
                action=action,
                actor_id=actor_id,
                target_type=target_type,
                target_id=target_id,
                metadata_json=metadata or {},
                created_at=_now(),
            )
        )
        session.commit()

def _audit_from_model(event: HubAuditEvent) -> dict[str, Any]:
    return {
        "id": event.id,
        "action": event.action,
        "actorId": event.actor_id,
        "targetType": event.target_type,
        "targetId": event.target_id,
        "metadata": event.metadata_json or {},
        "createdAt": event.created_at,
    }

def list_audit_events(
    *,
    actor_id: str,
    action: str | None,
    limit: int | None,
    is_admin: bool,
) -> list[dict[str, Any]]:
    with SessionLocal() as session:
        stmt = select(HubAuditEvent)
        if not is_admin:
            stmt = stmt.where(HubAuditEvent.actor_id == actor_id)
        if action:
            stmt = stmt.where(HubAuditEvent.action == action)
        stmt = stmt.order_by(HubAuditEvent.created_at.desc())
        if limit:
            stmt = stmt.limit(limit)
        events = session.execute(stmt).scalars().all()
        return [_audit_from_model(event) for event in events]
