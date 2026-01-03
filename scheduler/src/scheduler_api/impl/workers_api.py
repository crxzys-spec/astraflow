from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from urllib.parse import quote

from scheduler_api.http.errors import bad_request, forbidden, not_found

from scheduler_api.apis.workers_api_base import BaseWorkersApi
from scheduler_api.auth.roles import RUN_VIEW_ROLES, WORKFLOW_EDIT_ROLES, require_roles
from scheduler_api.config.settings import get_api_settings
from scheduler_api.infra.network import WorkerSession, worker_gateway
from scheduler_api.models.command_ref import CommandRef
from scheduler_api.models.list_workers200_response import ListWorkers200Response
from scheduler_api.models.worker import Worker
from scheduler_api.models.worker_capabilities import WorkerCapabilities
from scheduler_api.models.worker_capabilities_concurrency import WorkerCapabilitiesConcurrency
from scheduler_api.models.worker_command import WorkerCommand
from scheduler_api.models.worker_heartbeat_metrics import WorkerHeartbeatMetrics
from scheduler_api.models.worker_heartbeat_snapshot import WorkerHeartbeatSnapshot
from scheduler_api.models.worker_heartbeat_snapshot_packages import WorkerHeartbeatSnapshotPackages
from scheduler_api.models.worker_package import WorkerPackage
from scheduler_api.models.worker_package_status import WorkerPackageStatus
from scheduler_api.service.package_index import (
    PublishedPackageNotFoundError,
    PublishedPackageVersionNotFoundError,
    package_index_service,
)
from scheduler_api.service.package_registry import package_registry_service

from shared.models.biz.pkg.install import PackageInstallCommand
from shared.models.biz.pkg.uninstall import PackageUninstallCommand
from shared.models.session import Role, Sender, SessionDrainPayload, Status, WsEnvelope


class WorkersApiImpl(BaseWorkersApi):
    def __init__(self, tenant: str = "default") -> None:
        self.tenant = tenant

    async def list_workers(
        self,
        queue: Optional[str],
        connected: Optional[bool],
        registered: Optional[bool],
        healthy: Optional[bool],
        package_name: Optional[str],
        package_version: Optional[str],
        package_status: Optional[WorkerPackageStatus],
        max_heartbeat_age_seconds: Optional[float | int],
        max_inflight: Optional[int],
        max_latency_ms: Optional[int],
        limit: Optional[int],
        cursor: Optional[str],
    ) -> ListWorkers200Response:
        require_roles(*RUN_VIEW_ROLES)
        del cursor  # cursor pagination reserved for future implementation

        mapped_status = _map_api_package_status(package_status)
        if package_status is not None and mapped_status is None:
            return ListWorkers200Response(items=[], next_cursor=None)

        sessions = worker_gateway.query(
            tenant=self.tenant,
            connected=connected,
            registered=registered,
            require_healthy=healthy,
            max_heartbeat_age_seconds=(
                float(max_heartbeat_age_seconds)
                if max_heartbeat_age_seconds is not None
                else None
            ),
            package_name=package_name,
            package_version=package_version,
            package_status=mapped_status or Status.installed,
            max_inflight=max_inflight,
            max_latency_ms=max_latency_ms,
        )

        if queue:
            sessions = [
                session
                for session in sessions
                if queue in (session.channels or [])
            ]

        sessions.sort(key=lambda session: (session.worker_name, session.worker_instance_id))
        capped_limit = limit or 50
        items = [_session_to_worker(session) for session in sessions[:capped_limit]]
        return ListWorkers200Response(items=items, next_cursor=None)

    async def get_worker(
        self,
        workerName: str,
    ) -> Worker:
        require_roles(*RUN_VIEW_ROLES)
        session = _select_worker(workerName, tenant=self.tenant)
        if not session:
            raise not_found(f"Worker {workerName} not found", error="worker_not_found")
        return _session_to_worker(session)

    async def send_worker_command(
        self,
        workerName: str,
        worker_command: WorkerCommand,
        idempotency_key: Optional[str],
    ) -> CommandRef:
        token = require_roles(*WORKFLOW_EDIT_ROLES)
        del idempotency_key

        if worker_command is None:
            raise bad_request("worker_command body is required")

        payload = worker_command.to_dict() or {}
        if not isinstance(payload, dict):
            raise bad_request("worker_command payload must be an object")
        command_type = payload.get("type")
        if not command_type:
            raise bad_request("worker_command.type is required")

        session = _select_worker(workerName, tenant=self.tenant, require_connected=True)
        if not session:
            raise not_found(f"Worker {workerName} not connected", error="worker_not_connected")

        command_id = str(uuid4())
        envelope = _build_command_envelope(
            session=session,
            command_id=command_id,
            command_type=command_type,
            payload=payload,
            actor_id=token.sub if token else None,
            is_admin="admin" in (token.roles if token else []),
        )

        await worker_gateway.send_envelope(session, envelope)
        return CommandRef(
            command_id=command_id,
            worker_name=session.worker_name,
            accepted_at=datetime.now(timezone.utc),
        )


def _session_to_worker(session: WorkerSession) -> Worker:
    packages = [
        WorkerPackage(
            name=package.name,
            version=package.version,
            status=_map_session_package_status(package.status),
        )
        for package in session.packages
    ]
    capabilities = _build_capabilities(session)
    heartbeat = _build_heartbeat(session)
    payload_types = session.payload_types or None
    return Worker(
        id=session.worker_name,
        hostname=session.hostname or None,
        last_heartbeat_at=session.last_heartbeat,
        queues=session.channels or [],
        packages=packages or None,
        meta=None,
        connected=bool(session.transport),
        registered=session.registered,
        tenant=session.tenant,
        instance_id=session.worker_instance_id,
        version=session.version,
        capabilities=capabilities,
        payload_types=payload_types,
        heartbeat=heartbeat,
    )


def _build_capabilities(session: WorkerSession) -> Optional[WorkerCapabilities]:
    capabilities = session.capabilities
    if not capabilities:
        return None
    concurrency = capabilities.concurrency
    concurrency_payload = None
    if concurrency:
        concurrency_payload = WorkerCapabilitiesConcurrency(
            max_parallel=concurrency.max_parallel,
            per_node_limits=concurrency.per_node_limits,
        )
    runtimes = [runtime.root for runtime in capabilities.runtimes] if capabilities.runtimes else None
    features = list(capabilities.features) if capabilities.features else None
    return WorkerCapabilities(
        concurrency=concurrency_payload,
        runtimes=runtimes,
        features=features,
    )


def _build_heartbeat(session: WorkerSession) -> Optional[WorkerHeartbeatSnapshot]:
    heartbeat = session.heartbeat
    if not heartbeat:
        return None
    metrics = None
    if heartbeat.metrics:
        raw_metrics = heartbeat.metrics.model_dump(exclude_none=True)
        metrics_payload = {}
        for key, value in raw_metrics.items():
            if key == "cpu_pct":
                metrics_payload["cpuPct"] = value
            elif key == "mem_pct":
                metrics_payload["memPct"] = value
            elif key == "disk_pct":
                metrics_payload["diskPct"] = value
            elif key == "latency_ms":
                metrics_payload["latencyMs"] = value
            else:
                metrics_payload[key] = value
        metrics = WorkerHeartbeatMetrics.from_dict(metrics_payload)
    packages = None
    if heartbeat.packages:
        packages = WorkerHeartbeatSnapshotPackages(drift=heartbeat.packages.drift)
    return WorkerHeartbeatSnapshot(
        healthy=heartbeat.healthy,
        metrics=metrics,
        packages=packages,
    )


def _map_api_package_status(status: Optional[WorkerPackageStatus]) -> Optional[Status]:
    if status is None:
        return None
    try:
        return Status(status.value)
    except ValueError:
        return None


def _map_session_package_status(status: Optional[Status]) -> Optional[WorkerPackageStatus]:
    if status is None:
        return None
    try:
        return WorkerPackageStatus(status.value)
    except ValueError:
        return WorkerPackageStatus.UNKNOWN


def _select_worker(
    worker_name: str,
    *,
    tenant: str,
    require_connected: bool = False,
) -> Optional[WorkerSession]:
    sessions = worker_gateway.query(
        tenant=tenant,
        worker_name=worker_name,
        connected=True if require_connected else None,
        registered=True if require_connected else None,
    )
    if not sessions:
        return None
    if require_connected:
        return sessions[0]
    for session in sessions:
        if session.transport and session.registered:
            return session
    return sessions[0]


def _build_command_envelope(
    *,
    session: WorkerSession,
    command_id: str,
    command_type: str,
    payload: dict,
    actor_id: str | None,
    is_admin: bool,
) -> WsEnvelope:
    if command_type == "drain":
        command_payload = SessionDrainPayload().model_dump(by_alias=True, exclude_none=True)
        envelope_type = "control.drain"
    elif command_type == "pkg.install":
        name = payload.get("name")
        version = payload.get("version")
        if not name or not version:
            raise bad_request("pkg.install requires name and version")
        registry = package_registry_service.get(name)
        if registry and not package_registry_service.can_read(
            registry,
            actor_id=actor_id or "",
            is_admin=is_admin,
        ):
            raise forbidden("Package is private.")
        url = payload.get("url")
        sha256 = payload.get("sha256")
        detail = None
        if not url or not sha256:
            try:
                detail = package_index_service.get_package_detail(name, version)
            except PublishedPackageNotFoundError as exc:
                raise not_found(str(exc), error="package_not_found") from exc
            except PublishedPackageVersionNotFoundError as exc:
                raise not_found(str(exc), error="package_version_not_found") from exc
        if not url:
            base_url = _build_public_base_url()
            quoted_name = quote(str(name), safe="")
            quoted_version = quote(str(version), safe="")
            url = f"{base_url}/api/v1/published-packages/{quoted_name}/archive?version={quoted_version}"
        if not sha256:
            sha256 = detail.get("archiveSha256") if detail else None
        if not sha256:
            raise bad_request("pkg.install requires sha256 checksum for integrity checks")
        command_payload = PackageInstallCommand(
            name=name,
            version=version,
            url=url,
            sha256=sha256,
        ).model_dump(by_alias=True, exclude_none=True)
        envelope_type = "biz.pkg.install"
    elif command_type == "pkg.uninstall":
        name = payload.get("name")
        if not name:
            raise bad_request("pkg.uninstall requires name")
        command_payload = PackageUninstallCommand(
            name=name,
            version=payload.get("version"),
        ).model_dump(by_alias=True, exclude_none=True)
        envelope_type = "biz.pkg.uninstall"
    elif command_type == "rebind":
        raise bad_request("rebind not supported")
    else:
        raise bad_request(f"Unsupported worker_command.type {command_type}")

    return WsEnvelope(
        type=envelope_type,
        id=command_id,
        ts=datetime.now(timezone.utc),
        corr=command_id,
        seq=None,
        tenant=session.tenant,
        sender=Sender(role=Role.scheduler, id=worker_gateway.scheduler_id),
        payload=command_payload,
    )


def _build_public_base_url() -> str:
    settings = get_api_settings()
    if settings.public_base_url:
        return settings.public_base_url.rstrip("/")
    return f"http://{settings.host}:{settings.port}"
