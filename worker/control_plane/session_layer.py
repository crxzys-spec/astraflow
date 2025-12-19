"""Session-layer protocol helpers for the worker control-plane connection."""

from __future__ import annotations

import logging
import socket
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Optional

from pydantic import BaseModel

from shared.models.session import HandshakePayload, HeartbeatPayload, RegisterPayload, SessionResumePayload
from shared.models.session.handshake import Auth, Mode, Worker
from shared.models.session.heartbeat import Metrics
from shared.models.session.register import Capabilities, Concurrency

from worker.agent.concurrency import ConcurrencyGuard
from worker.agent.resource_registry import ResourceRegistry
from worker.config import WorkerSettings

LOGGER = logging.getLogger(__name__)

Payload = dict[str, Any] | BaseModel


@dataclass
class SessionLayer:
    """Builds and sends session-level frames (control.*)."""

    settings: WorkerSettings
    build_envelope: Callable[..., dict[str, Any]]
    send: Callable[[dict[str, Any]], Awaitable[None]]
    concurrency_guard: ConcurrencyGuard
    resource_registry: Optional[ResourceRegistry] = None

    async def send_handshake(self) -> None:
        message = self.build_handshake_envelope()
        await self.send(message)
        LOGGER.debug("Handshake payload dispatched")

    async def send_register(self) -> None:
        message = self.build_register_envelope()
        await self.send(message)
        LOGGER.debug("Register payload dispatched")

    async def send_resume(self, *, session_id: str, session_token: str, last_seen_seq: Optional[int] = None) -> None:
        payload = self.build_resume_payload(
            session_id=session_id,
            session_token=session_token,
            last_seen_seq=last_seen_seq,
        )
        message = self.build_envelope("control.resume", payload, request_ack=True)
        await self.send(message)
        LOGGER.debug("Resume payload dispatched")

    def build_handshake_envelope(self) -> dict[str, Any]:
        payload = self.build_handshake_payload()
        return self.build_envelope("control.handshake", payload, request_ack=True)

    def build_register_envelope(self) -> dict[str, Any]:
        payload = self.build_register_payload()
        return self.build_envelope("control.register", payload, request_ack=True)

    def build_handshake_payload(self) -> HandshakePayload:
        mode = Mode(self.settings.auth_mode)
        auth_kwargs: dict[str, Any] = {"mode": mode}
        if mode == Mode.token and self.settings.auth_token:
            auth_kwargs["token"] = self.settings.auth_token
        elif mode == Mode.mtls and self.settings.auth_fingerprint:
            auth_kwargs["fingerprint"] = self.settings.auth_fingerprint
        auth = Auth(**auth_kwargs)
        worker_info = Worker(
            worker_name=self.settings.worker_name,
            worker_instance_id=self.settings.worker_instance_id,
            version=self.settings.worker_version,
            hostname=socket.gethostname(),
        )
        return HandshakePayload(
            protocol=self.settings.handshake_protocol_version,
            auth=auth,
            worker=worker_info,
        )

    def build_register_payload(self) -> RegisterPayload:
        runtimes = list(self.settings.runtime_names or ["python"])
        concurrency = Concurrency(
            max_parallel=self.settings.concurrency_max_parallel,
            per_node_limits=self.settings.concurrency_per_node_limits,
        )
        capabilities = Capabilities(
            concurrency=concurrency,
            runtimes=runtimes,
            features=self.settings.feature_flags or [],
        )
        return RegisterPayload(
            capabilities=capabilities,
            payload_types=getattr(self.settings, "payload_types", None) or [],
        )

    def build_resume_payload(
        self,
        *,
        session_id: str,
        session_token: str,
        last_seen_seq: Optional[int] = None,
    ) -> SessionResumePayload:
        return SessionResumePayload(
            session_id=session_id,
            session_token=session_token,
            last_seen_seq=last_seen_seq,
        )

    def build_heartbeat_payload(self) -> HeartbeatPayload:
        metrics_payload: dict[str, Any] = {
            "inflight": self.concurrency_guard.inflight(),
        }
        if self.resource_registry:
            handles = self.resource_registry.list()
            metrics_payload["resource_handles"] = len(handles)
            metrics_payload["resource_bytes"] = sum(handle.size_bytes or 0 for handle in handles)
        metrics = Metrics(**metrics_payload)
        return HeartbeatPayload(
            healthy=True,
            metrics=metrics,
        )

    async def build_heartbeat_envelope(self) -> dict[str, Any]:
        payload = self.build_heartbeat_payload()
        message = self.build_envelope("control.heartbeat", payload)
        LOGGER.debug("Heartbeat payload built")
        return message
