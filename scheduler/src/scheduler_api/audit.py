"""Lightweight helpers for recording audit events."""

from __future__ import annotations

import json
from typing import Any, Mapping

from scheduler_api.db.models import AuditEventRecord
from scheduler_api.db.session import run_in_session
from scheduler_api.repo.audit import AuditRepository


_audit_repo = AuditRepository()


def record_audit_event(
    *,
    actor_id: str | None,
    action: str,
    target_type: str,
    target_id: str | None,
    metadata: Mapping[str, Any] | None = None,
) -> None:
    payload = None
    if metadata:
        try:
            payload = json.dumps(metadata, ensure_ascii=False)
        except (TypeError, ValueError):
            payload = json.dumps({"error": "serialization_failed"})

    def _create(session) -> None:
        _audit_repo.create_event(
            AuditEventRecord(
                actor_id=actor_id,
                action=action,
                target_type=target_type,
                target_id=target_id,
                details=payload,
            ),
            session=session,
        )

    run_in_session(_create)
