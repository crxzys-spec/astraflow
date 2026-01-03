"""Service layer for audit events."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Optional

from scheduler_api.db.session import run_in_session
from scheduler_api.models.list_audit_events200_response_items_inner import (
    ListAuditEvents200ResponseItemsInner,
)
from scheduler_api.repo.audit import AuditRepository


def _decode_cursor(cursor: Optional[str]) -> tuple[datetime, str] | None:
    if not cursor:
        return None
    try:
        timestamp, event_id = cursor.split("|", 1)
        return datetime.fromisoformat(timestamp), event_id
    except ValueError:
        return None


class AuditService:
    def __init__(self, repo: Optional[AuditRepository] = None) -> None:
        self._repo = repo or AuditRepository()

    def list_events(
        self,
        *,
        limit: Optional[int],
        cursor: Optional[str],
        action: Optional[str],
        actor_id: Optional[str],
        target_type: Optional[str],
    ) -> tuple[list[ListAuditEvents200ResponseItemsInner], Optional[str]]:
        page_size = min(max(limit or 50, 1), 200)
        cursor_value = _decode_cursor(cursor)
        def _list(session):
            return self._repo.list_events(
                limit=page_size,
                cursor_value=cursor_value,
                action=action,
                actor_id=actor_id,
                target_type=target_type,
                session=session,
            )

        rows = run_in_session(_list)

        next_cursor = None
        if len(rows) > page_size:
            last = rows[page_size - 1]
            next_cursor = f"{last.created_at.isoformat()}|{last.id}"
            rows = rows[:page_size]

        items: list[ListAuditEvents200ResponseItemsInner] = []
        for row in rows:
            metadata = None
            if row.details:
                try:
                    metadata = json.loads(row.details)
                except json.JSONDecodeError:
                    metadata = {"raw": row.details}
            items.append(
                ListAuditEvents200ResponseItemsInner(
                    eventId=row.id,
                    actorId=row.actor_id,
                    action=row.action,
                    targetType=row.target_type,
                    targetId=row.target_id,
                    metadata=metadata,
                    createdAt=row.created_at,
                )
            )
        return items, next_cursor


__all__ = ["AuditService"]
