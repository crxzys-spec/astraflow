from __future__ import annotations

import json
from datetime import datetime
from typing import Optional

from sqlalchemy import and_, or_

from scheduler_api.apis.audit_api_base import BaseAuditApi
from scheduler_api.auth.roles import AUDIT_VIEW_ROLES, require_roles
from scheduler_api.db.models import AuditEventRecord
from scheduler_api.db.session import SessionLocal
from scheduler_api.models.list_audit_events200_response import ListAuditEvents200Response
from scheduler_api.models.list_audit_events200_response_items_inner import (
    ListAuditEvents200ResponseItemsInner,
)


def _decode_cursor(cursor: Optional[str]) -> tuple[datetime, str] | None:
    if not cursor:
        return None
    try:
        timestamp, event_id = cursor.split("|", 1)
        return datetime.fromisoformat(timestamp), event_id
    except ValueError:
        return None


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
        page_size = min(max(limit or 50, 1), 200)
        cursor_value = _decode_cursor(cursor)

        with SessionLocal() as session:
            query = session.query(AuditEventRecord)
            if action:
                query = query.filter(AuditEventRecord.action == action)
            if actor_id:
                query = query.filter(AuditEventRecord.actor_id == actor_id)
            if target_type:
                query = query.filter(AuditEventRecord.target_type == target_type)
            if cursor_value:
                created_at, event_id = cursor_value
                query = query.filter(
                    or_(
                        AuditEventRecord.created_at < created_at,
                        and_(
                            AuditEventRecord.created_at == created_at,
                            AuditEventRecord.id < event_id,
                        ),
                    )
                )
            rows = (
                query.order_by(AuditEventRecord.created_at.desc(), AuditEventRecord.id.desc())
                .limit(page_size + 1)
                .all()
            )

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

        return ListAuditEvents200Response(items=items, nextCursor=next_cursor)
