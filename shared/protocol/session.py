"""Helpers for building/parsing session-level control frames."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

from pydantic import BaseModel

from shared.models.session import (
    Ack as AckModel,
    Capabilities,
    Concurrency,
    HandshakePayload,
    HeartbeatPayload,
    Metrics,
    RegisterPayload,
    Role,
    Sender,
    WsEnvelope,
)

Payload = Dict[str, Any] | BaseModel


def _payload_dict(payload: Payload) -> Dict[str, Any]:
    if isinstance(payload, BaseModel):
        return payload.model_dump(exclude_none=True, by_alias=True)
    return payload


def build_envelope(
    message_type: str,
    payload: Payload,
    *,
    tenant: str,
    sender_role: Role,
    sender_id: str,
    corr: Optional[str] = None,
    seq: Optional[int] = None,
    session_seq: Optional[int] = None,
    request_ack: bool = False,
    flags: Optional[Iterable[str]] = None,
    ts: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Construct an envelope dict ready for transport."""

    envelope = WsEnvelope(
        type=message_type,
        id=f"{message_type}-{int(datetime.now(timezone.utc).timestamp() * 1_000_000)}",
        ts=ts or datetime.now(timezone.utc),
        corr=corr,
        seq=seq,
        session_seq=session_seq,
        tenant=tenant,
        sender=Sender(role=sender_role, id=sender_id),
        ack=AckModel(request=True) if request_ack else None,
        flags=list(flags) if flags else None,
        payload=_payload_dict(payload),
    )
    data = envelope.model_dump(by_alias=True, exclude_none=True)
    data["ts"] = envelope.ts.isoformat()
    return data


def build_ack_for(target_envelope: WsEnvelope, *, sender_role: Role, sender_id: str) -> Dict[str, Any]:
    """Build an ack envelope referencing a received frame."""

    ack_payload = {"for": target_envelope.id}
    return build_envelope(
        "control.ack",
        payload=ack_payload,
        tenant=target_envelope.tenant,
        sender_role=sender_role,
        sender_id=sender_id,
        corr=target_envelope.corr,
        seq=target_envelope.seq,
        session_seq=target_envelope.session_seq,
        request_ack=False,
    )


def parse_envelope(raw: Dict[str, Any]) -> WsEnvelope:
    """Validate and parse a raw envelope dict."""

    return WsEnvelope.model_validate(raw)


def make_handshake_payload(*, protocol: int, mode: str, token: Optional[str], fingerprint: Optional[str], worker_name: str, worker_version: str, hostname: str) -> HandshakePayload:
    """Helper to construct a HandshakePayload."""

    from shared.models.session.handshake import Mode, Auth, Worker

    auth_kwargs: Dict[str, Any] = {"mode": Mode(mode)}
    if token:
        auth_kwargs["token"] = token
    if fingerprint:
        auth_kwargs["fingerprint"] = fingerprint
    return HandshakePayload(
        protocol=protocol,
        auth=Auth(**auth_kwargs),
        worker=Worker(worker_name=worker_name, version=worker_version, hostname=hostname),
    )


def make_register_payload(
    *,
    max_parallel: int,
    per_node_limits: Optional[Dict[str, int]],
    runtimes: List[str],
    features: List[str],
    payload_types: Optional[List[str]] = None,
) -> RegisterPayload:
    """Helper to construct a RegisterPayload."""

    concurrency = Concurrency(max_parallel=max_parallel, per_node_limits=per_node_limits)
    capabilities = Capabilities(
        concurrency=concurrency,
        runtimes=runtimes,
        features=features,
    )
    return RegisterPayload(
        capabilities=capabilities,
        payload_types=payload_types or [],
    )


def make_heartbeat_payload(
    *,
    healthy: bool,
    inflight: int,
    cpu_pct: Optional[float] = None,
    mem_pct: Optional[float] = None,
    disk_pct: Optional[float] = None,
    latency_ms: Optional[int] = None,
    packages: Optional[Dict[str, Any]] = None,
) -> HeartbeatPayload:
    """Helper to construct a HeartbeatPayload."""

    metrics = Metrics(
        inflight=inflight,
        cpu_pct=cpu_pct,
        mem_pct=mem_pct,
        disk_pct=disk_pct,
        latency_ms=latency_ms,
    )
    return HeartbeatPayload(
        healthy=healthy,
        metrics=metrics,
        packages=packages,  # packages block is optional/forwards-compatible
    )
