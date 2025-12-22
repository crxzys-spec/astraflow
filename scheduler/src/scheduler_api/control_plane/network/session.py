"""Session-layer handler for scheduler control-plane connections."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Callable, Optional
from uuid import uuid4

from websockets.exceptions import ConnectionClosedError, ConnectionClosedOK

from shared.models.session import (
    Ack,
    AckPayload,
    HandshakePayload,
    HeartbeatPayload,
    RegisterPayload,
    Role,
    Sender,
    SessionAcceptPayload,
    SessionResetPayload,
    SessionResumePayload,
    WsEnvelope,
)
from shared.models.session.handshake import Mode

from scheduler_api.config.settings import get_settings
from .events import publish_worker_heartbeat, publish_worker_package_updates
from .manager import WorkerControlManager, WorkerSession
from .session_tokens import issue_session_token, validate_session_token
from .transport import BaseTransport

LOGGER = logging.getLogger(__name__)


class ControlPlaneSession:
    """Handles session-level control frames for a worker connection."""

    def __init__(
        self,
        *,
        transport: BaseTransport,
        manager: WorkerControlManager,
        settings=None,
        scheduler_id: Optional[str] = None,
        token_issuer: Callable[..., tuple[str, float]] = issue_session_token,
        token_validator: Callable[..., bool] = validate_session_token,
    ) -> None:
        self._transport = transport
        self._manager = manager
        self._settings = settings or get_settings()
        self._scheduler_id = scheduler_id or manager.scheduler_id
        self._token_issuer = token_issuer
        self._token_validator = token_validator
        self._session: Optional[WorkerSession] = None
        self._closing = False

    @property
    def session(self) -> Optional[WorkerSession]:
        return self._session

    @property
    def closing(self) -> bool:
        return self._closing

    async def handle_envelope(self, envelope: WsEnvelope) -> list[WsEnvelope]:
        message_type = envelope.type

        if message_type == "control.resume":
            await self._handle_resume(envelope)
            return []

        if message_type == "control.handshake":
            await self._handle_handshake(envelope)
            return []

        if message_type == "control.register":
            await self._handle_register(envelope)
            return []

        if message_type == "control.heartbeat":
            await self._handle_heartbeat(envelope)
            return []

        if message_type == "control.ack":
            await self._handle_ack(envelope)
            return [envelope]

        if message_type.startswith("control."):
            await self._maybe_ack(envelope, session=self._session)
            LOGGER.warning("Unhandled control message type %s", message_type)
            return []

        if self._session and envelope.session_seq is not None and self._session.recv_window:
            ready, accepted = self._session.recv_window.record(envelope.session_seq, envelope)
            await self._maybe_ack(envelope, session=self._session, force=True)
            if not accepted:
                offset = envelope.session_seq - self._session.recv_window.base_seq - 1
                if envelope.session_seq in self._session.recv_window.buffer:
                    reason = "duplicate"
                elif offset >= self._session.recv_window.size:
                    reason = "out_of_window"
                elif envelope.session_seq <= self._session.recv_window.base_seq:
                    reason = "stale"
                else:
                    reason = "unknown"
                LOGGER.warning(
                    "Dropping message seq=%s type=%s reason=%s base_seq=%s window=%s",
                    envelope.session_seq,
                    envelope.type,
                    reason,
                    self._session.recv_window.base_seq,
                    self._session.recv_window.size,
                )
                return []
            return ready

        await self._maybe_ack(envelope, session=self._session)
        return [envelope]

    async def _handle_resume(self, envelope: WsEnvelope) -> None:
        resume = SessionResumePayload.model_validate(envelope.payload)
        worker_instance_id = envelope.sender.id
        session = self._manager.get_session(worker_instance_id, worker_name="")
        if not session:
            await self._send_reset(envelope, code="E.SESSION.UNKNOWN", reason="Unknown session")
            return
        if session.tenant != envelope.tenant:
            await self._send_reset(envelope, code="E.SESSION.TENANT_MISMATCH", reason="Tenant mismatch")
            return
        if not session.registered or not session.session_id:
            await self._send_reset(envelope, code="E.SESSION.NOT_REGISTERED", reason="Session not registered")
            return
        if session.session_id != resume.session_id:
            await self._send_reset(envelope, code="E.SESSION.MISMATCH", reason="Session id mismatch")
            return
        if not self._token_validator(
            resume.session_token,
            session_id=resume.session_id,
            worker_instance_id=session.worker_instance_id,
            tenant=envelope.tenant,
        ):
            await self._send_reset(envelope, code="E.SESSION.INVALID_TOKEN", reason="Invalid session token")
            return
        bound = self._manager.bind_session(worker_instance_id, session.worker_name, self._transport)
        if not bound:
            await self._send_reset(envelope, code="E.SESSION.UNKNOWN", reason="Unknown session")
            return
        session = bound
        session.authenticated = True
        session.registered = True
        self._session = session
        await self._maybe_ack(envelope, session=session, force=True)
        accept_envelope = self._build_session_accept(session, tenant=envelope.tenant, resumed=True)
        await self._transport.send(accept_envelope)

    async def _handle_handshake(self, envelope: WsEnvelope) -> None:
        handshake = HandshakePayload.model_validate(envelope.payload)
        worker_instance_id = handshake.worker.worker_instance_id or str(uuid4())
        ok, code, reason = self._validate_worker_auth(handshake)
        if not ok:
            await self._send_reset(envelope, code=code, reason=reason)
            return
        session = self._manager.upsert_session(
            worker_name=handshake.worker.worker_name,
            worker_instance_id=worker_instance_id,
            tenant=envelope.tenant,
            version=handshake.worker.version,
            hostname=handshake.worker.hostname,
            transport=self._transport,
        )
        session.authenticated = True
        self._session = session
        LOGGER.info("Handshake received from worker %s (tenant=%s)", session.worker_name, session.tenant)
        await self._maybe_ack(envelope, session=session, force=True)

    async def _handle_register(self, envelope: WsEnvelope) -> None:
        if not self._session:
            LOGGER.warning("Register received before handshake; closing connection")
            await self._send_reset(
                envelope,
                code="E.AUTH.HANDSHAKE_REQUIRED",
                reason="handshake required",
            )
            return
        if not self._session.authenticated:
            await self._send_reset(
                envelope,
                code="E.AUTH.UNAUTHENTICATED",
                reason="unauthenticated session",
            )
            return
        register = RegisterPayload.model_validate(envelope.payload)
        was_registered = bool(self._session.registered)
        previous_packages = list(self._session.packages)
        self._manager.update_registration(
            self._session.worker_instance_id,
            self._session.worker_name,
            capabilities=register.capabilities,
            payload_types=register.payload_types or [],
            packages=register.packages or [],
            manifests=register.manifests or [],
            channels=register.channels or [],
        )
        self._session.registered = True
        if was_registered:
            LOGGER.info(
                "Worker %s updated registration payload types=%s",
                self._session.worker_name,
                register.payload_types or [],
            )
        else:
            LOGGER.info(
                "Worker %s registered payload types=%s",
                self._session.worker_name,
                register.payload_types or [],
            )
        await self._maybe_ack(envelope, session=self._session, force=True)
        if not was_registered:
            accept_envelope = self._build_session_accept(self._session, tenant=envelope.tenant, resumed=False)
            await self._transport.send(accept_envelope)
        await publish_worker_package_updates(
            self._session,
            previous=previous_packages,
            current=register.packages or [],
        )
        await publish_worker_heartbeat(self._session, heartbeat=self._session.heartbeat)

    async def _handle_heartbeat(self, envelope: WsEnvelope) -> None:
        heartbeat = HeartbeatPayload.model_validate(envelope.payload)
        if self._session:
            self._manager.mark_heartbeat(
                self._session.worker_instance_id,
                self._session.worker_name,
                heartbeat=heartbeat,
            )
        await self._maybe_ack(envelope, session=self._session)
        if self._session:
            await publish_worker_heartbeat(
                self._session,
                heartbeat=heartbeat,
                occurred_at=self._session.last_heartbeat,
            )

    async def _handle_ack(self, envelope: WsEnvelope) -> None:
        try:
            ack_payload = AckPayload.model_validate(envelope.payload or {})
        except Exception as exc:  # noqa: BLE001
            LOGGER.warning("Invalid ack payload: %s", exc)
            ack_payload = None
        if self._session and ack_payload:
            self._manager.apply_session_ack(self._session, ack_payload)

    def _validate_worker_auth(self, handshake: HandshakePayload) -> tuple[bool, str, str]:
        auth = handshake.auth
        if auth.mode == Mode.token:
            if not auth.token:
                return False, "E.AUTH.MISSING_TOKEN", "Missing auth token"
            allowed = self._settings.allowed_worker_tokens()
            if allowed and auth.token not in allowed:
                return False, "E.AUTH.INVALID_TOKEN", "Invalid auth token"
            if not allowed:
                LOGGER.warning("No worker auth tokens configured; accepting any token")
            return True, "", ""
        if auth.mode == Mode.mtls:
            if not auth.fingerprint:
                return False, "E.AUTH.MTLS_REQUIRED", "Missing mTLS fingerprint"
            return True, "", ""
        return False, "E.AUTH.MODE_UNSUPPORTED", "Unsupported auth mode"

    async def _send_reset(self, envelope: WsEnvelope, *, code: str, reason: str) -> None:
        reset_payload = SessionResetPayload(code=code, reason=reason)
        reset_envelope = WsEnvelope(
            type="control.reset",
            id=str(uuid4()),
            ts=datetime.now(timezone.utc),
            corr=envelope.corr,
            seq=None,
            tenant=envelope.tenant,
            sender=Sender(role=Role.scheduler, id=self._scheduler_id),
            payload=reset_payload.model_dump(by_alias=True, exclude_none=True),
        )
        self._closing = True
        await self._transport.send(reset_envelope)
        await self._transport.close(code=1011, reason=reason)

    def _build_session_accept(self, session: WorkerSession, *, tenant: str, resumed: bool) -> WsEnvelope:
        if not session.session_id:
            session.session_id = str(uuid4())
        token, expires_at = self._token_issuer(
            session_id=session.session_id,
            worker_instance_id=session.worker_instance_id,
            tenant=tenant,
        )
        session.session_token = token
        session.session_expires_at = datetime.fromtimestamp(expires_at, tz=timezone.utc)
        payload = SessionAcceptPayload(
            session_id=session.session_id,
            session_token=token,
            expires_at=session.session_expires_at,
            resumed=resumed,
            worker_instance_id=session.worker_instance_id,
        )
        return WsEnvelope(
            type="control.session.accept",
            id=str(uuid4()),
            ts=datetime.now(timezone.utc),
            corr=None,
            seq=None,
            tenant=tenant,
            sender=Sender(role=Role.scheduler, id=self._scheduler_id),
            payload=payload.model_dump(by_alias=True, exclude_none=True),
        )

    async def _maybe_ack(
        self,
        envelope: WsEnvelope,
        *,
        session: Optional[WorkerSession] = None,
        force: bool = False,
    ) -> None:
        requested = bool(envelope.ack and envelope.ack.request)
        LOGGER.debug(
            "Evaluating ack for envelope id=%s type=%s requested=%s force=%s",
            envelope.id,
            envelope.type,
            requested,
            force,
        )
        if not force and not requested:
            return
        include_for = requested
        LOGGER.debug(
            "Sending ack for envelope id=%s type=%s force=%s",
            envelope.id,
            envelope.type,
            force,
        )
        payload: dict[str, object] = {"ok": True}
        if include_for and envelope.id:
            payload["for"] = envelope.id
        if session and session.recv_window:
            base_seq, bitmap, window = session.recv_window.ack_state()
            payload["ack_seq"] = base_seq
            payload["ack_bitmap"] = bitmap
            payload["recv_window"] = window
        ack_envelope = WsEnvelope(
            type="control.ack",
            id=str(uuid4()),
            ts=datetime.now(timezone.utc),
            corr=envelope.corr,
            seq=None,
            tenant=envelope.tenant,
            sender=Sender(role=Role.scheduler, id=self._scheduler_id),
            ack=Ack(**{"for": envelope.id}) if include_for and envelope.id else None,
            payload=payload,
        )
        try:
            await self._transport.send(ack_envelope)
        except (ConnectionClosedOK, ConnectionClosedError):
            LOGGER.debug(
                "Ack send skipped: websocket already closed id=%s type=%s",
                envelope.id,
                envelope.type,
            )
