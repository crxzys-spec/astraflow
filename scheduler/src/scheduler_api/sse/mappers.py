from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .models import UiEventEnvelope, UiEventScope, UiEventType


def run_state_envelope(
    *,
    tenant: str,
    client_session_id: str,
    run_id: str,
    status: str,
    started_at: Optional[datetime] = None,
    finished_at: Optional[datetime] = None,
    reason: Optional[str] = None,
    occurred_at: Optional[datetime] = None,
    meta: Optional[Dict[str, Any]] = None,
) -> UiEventEnvelope:
    payload_raw = {
        "kind": UiEventType.RUN_STATUS.value,
        "runId": run_id,
        "status": status,
        "startedAt": started_at.isoformat() if started_at else None,
        "finishedAt": finished_at.isoformat() if finished_at else None,
        "reason": reason,
    }
    payload = {key: value for key, value in payload_raw.items() if value is not None}
    return UiEventEnvelope(
        id="pending",
        type=UiEventType.RUN_STATUS,
        occurredAt=occurred_at or datetime.now(timezone.utc),
        scope=UiEventScope(
            tenant=tenant,
            runId=run_id,
            clientSessionId=client_session_id,
        ),
        meta=meta,
        data=payload,
    )


def run_snapshot_envelope(
    *,
    tenant: str,
    client_session_id: str,
    run: Dict[str, Any],
    nodes: Optional[list[Dict[str, Any]]] = None,
    occurred_at: Optional[datetime] = None,
) -> UiEventEnvelope:
    payload_raw = {
        "kind": UiEventType.RUN_SNAPSHOT.value,
        "run": run,
        "nodes": nodes,
    }
    payload = {
        key: value
        for key, value in payload_raw.items()
        if value is not None
    }
    return UiEventEnvelope(
        id="pending",
        type=UiEventType.RUN_SNAPSHOT,
        occurredAt=occurred_at or datetime.now(timezone.utc),
        scope=UiEventScope(
            tenant=tenant,
            runId=run.get("runId"),
            clientSessionId=client_session_id,
        ),
        data=payload,
    )


def node_state_envelope(
    *,
    tenant: str,
    client_session_id: str,
    run_id: str,
    node_id: str,
    stage: str,
    progress: Optional[float] = None,
    message: Optional[str] = None,
    error: Optional[Dict[str, Any]] = None,
    occurred_at: Optional[datetime] = None,
    last_updated_at: Optional[datetime] = None,
) -> UiEventEnvelope:
    state_raw = {
        "kind": UiEventType.NODE_STATE.value,
        "runId": run_id,
        "nodeId": node_id,
        "state": {
            "stage": stage,
            "progress": progress,
            "lastUpdatedAt": last_updated_at.isoformat() if last_updated_at else None,
            "message": message,
            "error": error,
        },
    }
    state = {
        key: value
        for key, value in state_raw["state"].items()
        if value is not None
    }
    payload = {
        **{key: value for key, value in state_raw.items() if key != "state"},
        "state": state,
    }
    return UiEventEnvelope(
        id="pending",
        type=UiEventType.NODE_STATE,
        occurredAt=occurred_at or datetime.now(timezone.utc),
        scope=UiEventScope(
            tenant=tenant,
            runId=run_id,
            clientSessionId=client_session_id,
        ),
        data=payload,
    )


def node_result_snapshot_envelope(
    *,
    tenant: str,
    client_session_id: str,
    run_id: str,
    node_id: str,
    revision: int,
    content: Optional[Dict[str, Any]],
    artifacts: Optional[list[Dict[str, Any]]],
    complete: bool,
    summary: Optional[str] = None,
    occurred_at: Optional[datetime] = None,
) -> UiEventEnvelope:
    payload_raw = {
        "kind": UiEventType.NODE_RESULT_SNAPSHOT.value,
        "runId": run_id,
        "nodeId": node_id,
        "revision": max(revision, 0),
        "format": "json",
        "content": content or {},
        "artifacts": artifacts or [],
        "summary": summary,
        "complete": complete,
    }
    payload = {
        key: value
        for key, value in payload_raw.items()
        if value is not None
    }
    return UiEventEnvelope(
        id="pending",
        type=UiEventType.NODE_RESULT_SNAPSHOT,
        occurredAt=occurred_at or datetime.now(timezone.utc),
        scope=UiEventScope(
            tenant=tenant,
            runId=run_id,
            clientSessionId=client_session_id,
        ),
        data=payload,
    )


def node_result_delta_envelope(
    *,
    tenant: str,
    client_session_id: str,
    run_id: str,
    node_id: str,
    revision: int,
    sequence: int,
    operation: str,
    path: Optional[str] = None,
    payload: Optional[Dict[str, Any]] = None,
    chunk_meta: Optional[Dict[str, Any]] = None,
    terminal: bool = False,
    occurred_at: Optional[datetime] = None,
) -> UiEventEnvelope:
    payload_raw = {
        "kind": UiEventType.NODE_RESULT_DELTA.value,
        "runId": run_id,
        "nodeId": node_id,
        "revision": max(revision, 0),
        "sequence": max(sequence, 0),
        "operation": operation,
        "path": path,
        "payload": payload,
        "chunkMeta": chunk_meta,
        "terminal": terminal,
    }
    event_payload = {
        key: value
        for key, value in payload_raw.items()
        if value is not None
    }
    return UiEventEnvelope(
        id="pending",
        type=UiEventType.NODE_RESULT_DELTA,
        occurredAt=occurred_at or datetime.now(timezone.utc),
        scope=UiEventScope(
            tenant=tenant,
            runId=run_id,
            clientSessionId=client_session_id,
        ),
        data=event_payload,
    )


def worker_heartbeat_envelope(
    *,
    tenant: str,
    worker_name: str,
    at: datetime,
    queues: Optional[list[str]] = None,
    instance_id: Optional[str] = None,
    hostname: Optional[str] = None,
    version: Optional[str] = None,
    connected: Optional[bool] = None,
    registered: Optional[bool] = None,
    heartbeat: Optional[Dict[str, Any]] = None,
    occurred_at: Optional[datetime] = None,
) -> UiEventEnvelope:
    payload_raw = {
        "kind": UiEventType.WORKER_HEARTBEAT.value,
        "workerName": worker_name,
        "at": at.isoformat(),
        "queues": queues,
        "instanceId": instance_id,
        "hostname": hostname,
        "version": version,
        "connected": connected,
        "registered": registered,
        "heartbeat": heartbeat,
    }
    payload = {
        key: value
        for key, value in payload_raw.items()
        if value is not None
    }
    return UiEventEnvelope(
        id="pending",
        type=UiEventType.WORKER_HEARTBEAT,
        occurredAt=occurred_at or datetime.now(timezone.utc),
        scope=UiEventScope(
            tenant=tenant,
            workerName=worker_name,
        ),
        data=payload,
    )


def worker_package_envelope(
    *,
    tenant: str,
    worker_name: str,
    package_name: str,
    version: Optional[str],
    status: str,
    message: Optional[str] = None,
    occurred_at: Optional[datetime] = None,
) -> UiEventEnvelope:
    payload_raw = {
        "kind": UiEventType.WORKER_PACKAGE.value,
        "workerName": worker_name,
        "package": package_name,
        "version": version,
        "status": status,
        "message": message,
    }
    payload = {
        key: value
        for key, value in payload_raw.items()
        if value is not None
    }
    return UiEventEnvelope(
        id="pending",
        type=UiEventType.WORKER_PACKAGE,
        occurredAt=occurred_at or datetime.now(timezone.utc),
        scope=UiEventScope(
            tenant=tenant,
            workerName=worker_name,
        ),
        data=payload,
    )

