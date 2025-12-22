from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Optional

from fastapi.encoders import jsonable_encoder

from shared.models.session import AckPayload, WsEnvelope, Capabilities, HeartbeatPayload
from shared.models.session.register import Package, Manifest
from shared.protocol.window import ReceiveWindow, is_seq_acked
from scheduler_api.config.settings import get_settings
from .transport import BaseTransport


def _session_window_size() -> int:
    settings = get_settings()
    return int(settings.session_window_size)


@dataclass
class WorkerSession:
    worker_name: str
    worker_instance_id: str
    tenant: str
    version: str
    hostname: str
    transport: Optional[BaseTransport]
    session_id: Optional[str] = None
    session_token: Optional[str] = None
    session_expires_at: Optional[datetime] = None
    authenticated: bool = False
    registered: bool = False
    last_heartbeat: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    capabilities: Optional[Capabilities] = None
    payload_types: list[str] = field(default_factory=list)
    packages: list[Package] = field(default_factory=list)
    manifests: list[Manifest] = field(default_factory=list)
    channels: list[str] = field(default_factory=list)
    heartbeat: Optional[HeartbeatPayload] = None
    recv_window: Optional[ReceiveWindow[WsEnvelope]] = None
    send_credit: Optional[asyncio.Semaphore] = None
    send_next_seq: int = 1
    seq_to_message_id: Dict[int, str] = field(default_factory=dict)
    send_lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    send_waiters: int = 0
    send_epoch: int = 0


class WorkerControlManager:
    """Tracks active worker connections."""

    def __init__(self, scheduler_id: str = "scheduler-control"):
        self.scheduler_id = scheduler_id
        self._sessions: Dict[str, WorkerSession] = {}
        self._session_window_size = _session_window_size()

    @staticmethod
    def _key(instance_id: Optional[str], worker_name: str) -> str:
        return instance_id or worker_name

    def upsert_session(
        self,
        *,
        worker_name: str,
        worker_instance_id: str,
        tenant: str,
        version: str,
        hostname: str,
        transport: BaseTransport,
    ) -> WorkerSession:
        """Register a worker session, replacing any previous connection."""

        key = self._key(worker_instance_id, worker_name)
        previous = self._sessions.get(key)
        if previous and previous.transport and previous.transport is not transport:
            asyncio.create_task(previous.transport.close(code=1011, reason="superseded session"))
        if previous:
            session = previous
            session.tenant = tenant
            session.version = version
            session.hostname = hostname
            session.transport = transport
            session.worker_name = worker_name
            session.worker_instance_id = worker_instance_id
        else:
            session = WorkerSession(
                worker_name=worker_name,
                worker_instance_id=worker_instance_id,
                tenant=tenant,
                version=version,
                hostname=hostname,
                transport=transport,
            )
            self._sessions[key] = session
        self._sessions[key] = session
        session.session_id = None
        session.session_token = None
        session.session_expires_at = None
        session.authenticated = False
        session.registered = False
        session.capabilities = None
        session.payload_types = []
        session.packages = []
        session.manifests = []
        session.channels = []
        session.heartbeat = None
        session.last_heartbeat = datetime.now(timezone.utc)
        self._reset_session_state(session)
        return session

    def _reset_session_state(self, session: WorkerSession) -> None:
        old_credit = session.send_credit
        waiters = session.send_waiters
        if old_credit and waiters:
            for _ in range(waiters):
                old_credit.release()
        session.recv_window = ReceiveWindow(self._session_window_size)
        session.send_credit = asyncio.Semaphore(self._session_window_size)
        session.send_next_seq = 1
        session.seq_to_message_id.clear()
        session.send_epoch += 1

    def rekey_session(self, old_key: str, new_key: str) -> None:
        if old_key == new_key:
            return
        session = self._sessions.pop(old_key, None)
        if session:
            self._sessions[new_key] = session

    async def _assign_session_seq(self, session: WorkerSession, envelope: dict) -> Optional[int]:
        message_type = envelope.get("type") or ""
        if message_type.startswith("control."):
            return None
        if envelope.get("session_seq") is not None:
            return envelope.get("session_seq")
        if session.send_credit is None or session.recv_window is None:
            self._reset_session_state(session)
        if not session.send_credit:
            return None
        credit = session.send_credit
        epoch = session.send_epoch
        session.send_waiters += 1
        try:
            await credit.acquire()
        finally:
            session.send_waiters -= 1
        async with session.send_lock:
            if epoch != session.send_epoch:
                credit.release()
                raise RuntimeError("Session reset while waiting for send window")
            seq = session.send_next_seq
            session.send_next_seq += 1
            envelope["session_seq"] = seq
            session.seq_to_message_id[seq] = envelope.get("id") or ""
            return seq

    def _release_session_seq(self, session: WorkerSession, seq: Optional[int]) -> None:
        if seq is None:
            return
        message_id = session.seq_to_message_id.pop(seq, None)
        if message_id is None:
            return
        if session.send_credit:
            session.send_credit.release()

    def apply_session_ack(self, session: WorkerSession, payload: AckPayload) -> None:
        if payload.ack_seq is None:
            return
        window_size = payload.recv_window or self._session_window_size
        for seq in list(session.seq_to_message_id):
            if is_seq_acked(seq, payload.ack_seq, payload.ack_bitmap, window_size):
                self._release_session_seq(session, seq)

    def bind_session(self, worker_instance_id: str, worker_name: str, transport: BaseTransport) -> Optional[WorkerSession]:
        session = self._sessions.get(self._key(worker_instance_id, worker_name))
        if not session:
            return None
        if session.transport and session.transport is not transport:
            asyncio.create_task(session.transport.close(code=1011, reason="superseded session"))
        session.transport = transport
        session.last_heartbeat = datetime.now(timezone.utc)
        return session

    def remove_session(self, worker_name: str, worker_instance_id: Optional[str] = None) -> None:
        self._sessions.pop(self._key(worker_instance_id, worker_name), None)

    def mark_disconnected(self, worker_instance_id: Optional[str], worker_name: str) -> None:
        session = self._sessions.get(self._key(worker_instance_id, worker_name))
        if session:
            session.transport = None

    def get_session(self, worker_instance_id: Optional[str], worker_name: Optional[str]) -> Optional[WorkerSession]:
        if not worker_instance_id:
            return None
        return self._sessions.get(self._key(worker_instance_id, worker_name or ""))

    def update_registration(
        self,
        worker_instance_id: Optional[str],
        worker_name: str,
        *,
        capabilities: Capabilities,
        payload_types: list[str],
        packages: list[Package],
        manifests: list[Manifest],
        channels: list[str],
    ) -> None:
        session = self._sessions.get(self._key(worker_instance_id, worker_name))
        if not session:
            return
        session.capabilities = capabilities
        session.payload_types = payload_types
        session.packages = packages
        session.manifests = manifests
        session.channels = channels

    def mark_heartbeat(
        self,
        worker_instance_id: Optional[str],
        worker_name: str,
        *,
        heartbeat: Optional[HeartbeatPayload] = None,
    ) -> None:
        session = self._sessions.get(self._key(worker_instance_id, worker_name))
        if not session:
            return
        session.last_heartbeat = datetime.now(timezone.utc)
        if heartbeat is not None:
            session.heartbeat = heartbeat

    def select_session(self, *, tenant: str) -> Optional[WorkerSession]:
        for session in self._sessions.values():
            if session.tenant == tenant and session.transport and session.registered:
                return session
        return None

    async def send_envelope(self, worker: WorkerSession | str, payload: dict | WsEnvelope) -> None:
        if isinstance(worker, WorkerSession):
            key = self._key(worker.worker_instance_id, worker.worker_name)
            session = worker
        else:
            key = worker
            session = self._sessions.get(key)
        if not session or not session.transport:
            raise KeyError(f"Worker {key} not connected")
        if isinstance(payload, WsEnvelope):
            data = payload.model_dump(by_alias=True, exclude_none=True)
        else:
            data = jsonable_encoder(payload)
        if isinstance(data, dict):
            await self._assign_session_seq(session, data)
        await session.transport.send(data)

    def list_sessions(self) -> Dict[str, WorkerSession]:
        return dict(self._sessions)


worker_manager = WorkerControlManager()
