from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Optional
from uuid import uuid4

from fastapi import WebSocket
from fastapi.encoders import jsonable_encoder

from shared.models.ws.cmd.dispatch import CommandDispatchPayload
from shared.models.ws.envelope import Ack, Role, Sender, WsEnvelope
from shared.models.ws.register import Capabilities, Package


@dataclass
class WorkerSession:
    worker_id: str
    tenant: str
    version: str
    hostname: str
    websocket: WebSocket
    last_heartbeat: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    capabilities: Optional[Capabilities] = None
    packages: list[Package] = field(default_factory=list)


class WorkerControlManager:
    """Tracks active worker connections."""

    def __init__(self, scheduler_id: str = "scheduler-control"):
        self.scheduler_id = scheduler_id
        self._sessions: Dict[str, WorkerSession] = {}

    def upsert_session(
        self,
        *,
        worker_id: str,
        tenant: str,
        version: str,
        hostname: str,
        websocket: WebSocket,
    ) -> WorkerSession:
        """Register a worker session, replacing any previous connection."""

        previous = self._sessions.get(worker_id)
        if previous and previous.websocket is not websocket:
            asyncio.create_task(
                previous.websocket.close(code=1011, reason="superseded session")
            )
        session = WorkerSession(
            worker_id=worker_id,
            tenant=tenant,
            version=version,
            hostname=hostname,
            websocket=websocket,
        )
        self._sessions[worker_id] = session
        return session

    def remove_session(self, worker_id: str) -> None:
        self._sessions.pop(worker_id, None)

    def get_session(self, worker_id: str) -> Optional[WorkerSession]:
        return self._sessions.get(worker_id)

    def update_registration(
        self,
        worker_id: str,
        *,
        capabilities: Capabilities,
        packages: list[Package],
    ) -> None:
        session = self._sessions.get(worker_id)
        if not session:
            return
        session.capabilities = capabilities
        session.packages = packages

    def mark_heartbeat(self, worker_id: str) -> None:
        session = self._sessions.get(worker_id)
        if not session:
            return
        session.last_heartbeat = datetime.now(timezone.utc)

    def select_session(
        self,
        *,
        tenant: str,
        package_name: Optional[str] = None,
        package_version: Optional[str] = None,
    ) -> Optional[WorkerSession]:
        for session in self._sessions.values():
            if session.tenant != tenant:
                continue
            if package_name and package_version:
                if not any(
                    pkg.name == package_name and pkg.version == package_version
                    for pkg in session.packages
                ):
                    continue
            return session
        return None

    async def send_envelope(self, worker_id: str, payload: dict) -> None:
        session = self._sessions.get(worker_id)
        if not session:
            raise KeyError(f"Worker {worker_id} not connected")
        await session.websocket.send_text(json.dumps(jsonable_encoder(payload)))

    async def dispatch_command(
        self,
        session: WorkerSession,
        payload: CommandDispatchPayload,
        *,
        tenant: str,
        corr: str,
        seq: int,
        request_ack: bool = True,
    ) -> str:
        envelope = WsEnvelope(
            type="cmd.dispatch",
            id=str(uuid4()),
            ts=datetime.now(timezone.utc),
            corr=corr,
            seq=seq,
            tenant=tenant,
            sender=Sender(role=Role.scheduler, id=self.scheduler_id),
            ack=Ack(request=True) if request_ack else None,
            payload=payload.model_dump(by_alias=True, exclude_none=True),
        )
        data = envelope.model_dump(by_alias=True, exclude_none=True)
        data["ts"] = envelope.ts.isoformat()
        await session.websocket.send_text(json.dumps(jsonable_encoder(data)))
        return envelope.id

    def list_sessions(self) -> Dict[str, WorkerSession]:
        return dict(self._sessions)


worker_manager = WorkerControlManager()
