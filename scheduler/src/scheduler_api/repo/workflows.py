"""Repository for workflow records."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from scheduler_api.db.models import WorkflowRecord


class WorkflowRepository:
    def list_active(
        self,
        *,
        limit: int,
        owner_id: Optional[str],
        is_admin: bool,
        session: Session,
    ) -> list[WorkflowRecord]:
        stmt = (
            select(WorkflowRecord)
            .where(WorkflowRecord.deleted_at.is_(None))
            .order_by(WorkflowRecord.created_at.desc())
            .limit(limit)
        )
        if not is_admin and owner_id:
            stmt = stmt.where(
                or_(
                    WorkflowRecord.owner_id == owner_id,
                    and_(
                        WorkflowRecord.owner_id.is_(None),
                        WorkflowRecord.created_by == owner_id,
                    ),
                )
            )
        return list(session.execute(stmt).scalars().all())

    def get(
        self,
        workflow_id: str,
        *,
        session: Session,
    ) -> Optional[WorkflowRecord]:
        return session.get(WorkflowRecord, workflow_id)

    def save(
        self,
        record: WorkflowRecord,
        *,
        session: Session,
    ) -> WorkflowRecord:
        session.add(record)
        return record
