"""Facade for worker control-plane session access and outbound messaging."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable, Optional

from shared.models.session import WsEnvelope
from shared.models.session.register import Status as PackageStatus

from .manager import WorkerControlManager, WorkerSession, worker_manager


class WorkerGateway:
    """Single entrypoint for worker session access + outbound messaging."""

    def __init__(
        self,
        manager: WorkerControlManager = worker_manager,
        now_provider: Callable[[], datetime] | None = None,
    ) -> None:
        self._manager = manager
        self._now = now_provider or (lambda: datetime.now(timezone.utc))

    @property
    def scheduler_id(self) -> str:
        return self._manager.scheduler_id

    def select_session(self, *, tenant: str) -> Optional[WorkerSession]:
        return self._manager.select_session(tenant=tenant)

    def list_sessions(self) -> dict[str, WorkerSession]:
        return self._manager.list_sessions()

    def query(
        self,
        *,
        tenant: Optional[str] = None,
        worker_name: Optional[str] = None,
        worker_instance_id: Optional[str] = None,
        connected: Optional[bool] = None,
        registered: Optional[bool] = None,
        require_healthy: Optional[bool] = None,
        max_heartbeat_age_seconds: Optional[float] = None,
        package_name: Optional[str] = None,
        package_version: Optional[str] = None,
        package_status: PackageStatus = PackageStatus.installed,
        max_inflight: Optional[int] = None,
        max_latency_ms: Optional[int] = None,
    ) -> list[WorkerSession]:
        sessions = list(self._manager.list_sessions().values())
        if tenant is not None:
            sessions = [session for session in sessions if session.tenant == tenant]
        if worker_name is not None:
            sessions = [session for session in sessions if session.worker_name == worker_name]
        if worker_instance_id is not None:
            sessions = [session for session in sessions if session.worker_instance_id == worker_instance_id]
        if connected is not None:
            sessions = [session for session in sessions if bool(session.transport) == connected]
        if registered is not None:
            sessions = [session for session in sessions if session.registered == registered]
        now = self._now()
        for session in list(sessions):
            if require_healthy is not None:
                heartbeat = session.heartbeat
                if not heartbeat:
                    if require_healthy:
                        sessions.remove(session)
                    continue
                if heartbeat.healthy != require_healthy:
                    sessions.remove(session)
                    continue
            if max_heartbeat_age_seconds is not None:
                age = (now - session.last_heartbeat).total_seconds()
                if age > max_heartbeat_age_seconds:
                    sessions.remove(session)
                    continue
            if package_name or package_version:
                if not package_name or not package_version:
                    sessions.remove(session)
                    continue
                if not self._supports_package(session, package_name, package_version, package_status):
                    sessions.remove(session)
                    continue
            if max_inflight is not None:
                inflight = session.heartbeat.metrics.inflight if session.heartbeat else None
                if inflight is None or inflight > max_inflight:
                    sessions.remove(session)
                    continue
            if max_latency_ms is not None:
                latency = session.heartbeat.metrics.latency_ms if session.heartbeat else None
                if latency is None or latency > max_latency_ms:
                    sessions.remove(session)
                    continue
        return sessions

    async def send_envelope(self, worker: WorkerSession | str, payload: dict | WsEnvelope) -> None:
        await self._manager.send_envelope(worker, payload)

    @staticmethod
    def _supports_package(
        session: WorkerSession,
        package_name: str,
        package_version: str,
        status: PackageStatus,
    ) -> bool:
        for package in session.packages:
            if (
                package.name == package_name
                and package.version == package_version
                and package.status == status
            ):
                return True
        return False


worker_gateway = WorkerGateway()
