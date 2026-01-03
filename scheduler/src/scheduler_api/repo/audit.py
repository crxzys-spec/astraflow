"""Repository for audit events."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from scheduler_api.db.models import AuditEventRecord


class AuditRepository:
    def create_event(self, record: AuditEventRecord, *, session: Session) -> None:
        session.add(record)

    def list_events(
        self,
        *,
        limit: int,
        cursor_value: Optional[tuple[datetime, str]],
        action: Optional[str],
        actor_id: Optional[str],
        target_type: Optional[str],
        session: Session,
    ) -> list[AuditEventRecord]:
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
        return (
            query.order_by(AuditEventRecord.created_at.desc(), AuditEventRecord.id.desc())
            .limit(limit + 1)
            .all()
        )
