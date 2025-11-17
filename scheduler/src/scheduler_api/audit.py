"""Lightweight helpers for recording audit events."""

from __future__ import annotations

import json
from typing import Any, Mapping

from scheduler_api.db.models import AuditEventRecord
from scheduler_api.db.session import SessionLocal


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

    with SessionLocal() as session:
        session.add(
            AuditEventRecord(
                actor_id=actor_id,
                action=action,
                target_type=target_type,
                target_id=target_id,
                details=payload,
            )
        )
        session.commit()
