from __future__ import annotations

import json
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, ConfigDict


class UiEventType(str, Enum):
    RUN_STATUS = "run.status"
    RUN_SNAPSHOT = "run.snapshot"
    RUN_METRICS = "run.metrics"
    NODE_STATE = "node.state"
    NODE_STATUS = "node.status"
    NODE_RESULT_SNAPSHOT = "node.result.snapshot"
    NODE_RESULT_DELTA = "node.result.delta"
    NODE_ERROR = "node.error"
    ARTIFACT_READY = "artifact.ready"
    ARTIFACT_REMOVED = "artifact.removed"
    COMMAND_ACK = "command.ack"
    COMMAND_ERROR = "command.error"
    WORKER_HEARTBEAT = "worker.heartbeat"
    WORKER_PACKAGE = "worker.package"


class UiEventScope(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    tenant: str
    runId: Optional[str] = None
    workerName: Optional[str] = None
    clientSessionId: Optional[str] = None
    clientInstanceId: Optional[str] = None


class UiEventEnvelope(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="allow")

    version: str = "v1"
    id: str
    type: UiEventType
    occurredAt: datetime = Field(alias="occurredAt")
    scope: UiEventScope
    replayed: Optional[bool] = None
    correlationId: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None
    data: Dict[str, Any]


def serialize_envelope(envelope: UiEventEnvelope) -> bytes:
    """Serialize an envelope into an SSE frame."""
    payload = envelope.model_dump(by_alias=True, exclude_none=True, mode="json")
    event_type = payload.get("type")
    event_id = payload.get("id")
    json_payload = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    lines = []
    if event_id is not None:
        lines.append(f"id: {event_id}")
    if event_type is not None:
        lines.append(f"event: {event_type}")
    lines.append(f"data: {json_payload}")
    return ("\n".join(lines) + "\n\n").encode("utf-8")
