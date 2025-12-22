from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Dict, Iterable, Optional, Tuple

from scheduler_api.sse import event_publisher
from scheduler_api.sse.mappers import worker_heartbeat_envelope, worker_package_envelope
from shared.models.session import HeartbeatPayload
from shared.models.session.register import Package, Status

from .manager import WorkerSession

LOGGER = logging.getLogger(__name__)


def _format_heartbeat_snapshot(heartbeat: HeartbeatPayload) -> Dict[str, object]:
    metrics_payload = heartbeat.metrics.model_dump(exclude_none=True)
    metrics: Dict[str, object] = {}
    for key, value in metrics_payload.items():
        if key == "cpu_pct":
            metrics["cpuPct"] = value
        elif key == "mem_pct":
            metrics["memPct"] = value
        elif key == "disk_pct":
            metrics["diskPct"] = value
        elif key == "latency_ms":
            metrics["latencyMs"] = value
        else:
            metrics[key] = value

    payload: Dict[str, object] = {"healthy": heartbeat.healthy}
    if metrics:
        payload["metrics"] = metrics
    if heartbeat.packages:
        packages_payload: Dict[str, object] = {}
        if heartbeat.packages.drift is not None:
            packages_payload["drift"] = heartbeat.packages.drift
        if packages_payload:
            payload["packages"] = packages_payload
    return payload


async def publish_worker_heartbeat(
    session: WorkerSession,
    *,
    heartbeat: Optional[HeartbeatPayload] = None,
    occurred_at: Optional[datetime] = None,
) -> None:
    if not session:
        return
    timestamp = occurred_at or datetime.now(timezone.utc)
    snapshot = None
    heartbeat = heartbeat or session.heartbeat
    if heartbeat:
        snapshot = _format_heartbeat_snapshot(heartbeat)
    envelope = worker_heartbeat_envelope(
        tenant=session.tenant,
        worker_name=session.worker_name,
        at=timestamp,
        queues=session.channels,
        instance_id=session.worker_instance_id or None,
        hostname=session.hostname or None,
        version=session.version or None,
        connected=bool(session.transport),
        registered=session.registered,
        heartbeat=snapshot,
        occurred_at=timestamp,
    )
    try:
        await event_publisher.publish(envelope)
    except Exception:  # noqa: BLE001
        LOGGER.exception("Failed to publish worker heartbeat event worker=%s", session.worker_name)


def _package_key(package: Package) -> Tuple[str, str]:
    return (package.name, package.version)


def _map_package_status(status: Optional[Status]) -> str:
    if status is None:
        return "unknown"
    try:
        return str(Status(status).value)
    except Exception:  # noqa: BLE001
        return "unknown"


async def publish_worker_package_updates(
    session: WorkerSession,
    *,
    previous: Iterable[Package],
    current: Iterable[Package],
) -> None:
    if not session:
        return
    previous_map = {_package_key(package): package for package in previous}
    current_map = {_package_key(package): package for package in current}

    for key, package in current_map.items():
        prior = previous_map.get(key)
        if not prior or prior.status != package.status:
            await _publish_worker_package(session, package, status_override=_map_package_status(package.status))

    for key, package in previous_map.items():
        if key not in current_map:
            await _publish_worker_package(session, package, status_override="removed")


async def _publish_worker_package(
    session: WorkerSession,
    package: Package,
    *,
    status_override: Optional[str] = None,
    message: Optional[str] = None,
) -> None:
    envelope = worker_package_envelope(
        tenant=session.tenant,
        worker_name=session.worker_name,
        package_name=package.name,
        version=package.version,
        status=status_override or _map_package_status(package.status),
        message=message,
        occurred_at=datetime.now(timezone.utc),
    )
    try:
        await event_publisher.publish(envelope)
    except Exception:  # noqa: BLE001
        LOGGER.exception(
            "Failed to publish worker package event worker=%s package=%s",
            session.worker_name,
            package.name,
        )
