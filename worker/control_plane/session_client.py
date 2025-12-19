"""Pure session layer for the worker control-plane connection.

This layer is responsible for:
- Transport lifecycle (via ConnectionManager)
- Session control frames (handshake/register/heartbeat)
- Envelope framing/validation
- ACK bookkeeping (request/resolve/retry)

It must not depend on business protocol models (biz.*).
"""

from __future__ import annotations

import asyncio
import contextlib
import copy
import logging
from collections.abc import AsyncIterator, Awaitable, Callable, Iterator
from dataclasses import dataclass, field
from datetime import datetime, timezone
from itertools import count
from typing import Any, Optional

from pydantic import BaseModel, ValidationError

from shared.models.session import (
    Ack,
    AckPayload,
    Role,
    Sender,
    SessionAcceptPayload,
    SessionDrainPayload,
    SessionResetPayload,
    WsEnvelope,
)
from shared.protocol.window import ReceiveWindow, is_seq_acked

from worker.agent.concurrency import ConcurrencyGuard
from worker.agent.resource_registry import ResourceRegistry
from worker.config import WorkerSettings
from worker.control_plane.session import SessionState, SessionTracker
from worker.control_plane.session_layer import SessionLayer
from worker.transport import ConnectionError, ConnectionManager, ControlPlaneTransport

LOGGER = logging.getLogger(__name__)
WINDOW_STALL_WARN_SECONDS = 1.0


class TransportNotReady(RuntimeError):
    """Raised when control-plane IO is invoked without an established transport."""


class SessionResetError(RuntimeError):
    """Raised when the scheduler resets the session."""


class SessionAcceptTimeout(RuntimeError):
    """Raised when session accept does not arrive in time."""


@dataclass
class PendingAck:
    message: dict[str, Any]
    attempts: int = 0
    task: Optional[asyncio.Task[None]] = None
    future: Optional[asyncio.Future[None]] = None
    session_seq: Optional[int] = None


@dataclass
class ControlPlaneSession:
    """Worker-side session client for the scheduler control-plane."""

    settings: WorkerSettings
    transport_factory: Callable[[WorkerSettings], ControlPlaneTransport]
    concurrency_guard: ConcurrencyGuard = field(default_factory=ConcurrencyGuard)
    resource_registry: Optional[ResourceRegistry] = None
    session: SessionTracker = field(default_factory=SessionTracker)
    on_disconnect: Optional[Callable[[Exception], Awaitable[None]]] = None
    on_reconnect: Optional[Callable[[], Awaitable[None]]] = None
    on_ready: Optional[Callable[[bool], Awaitable[None]]] = None

    _manager: Optional[ConnectionManager] = None
    _receive_task: Optional[asyncio.Task[None]] = None
    _message_counter: Iterator[int] = field(default_factory=lambda: count())
    _pending_acks: dict[str, PendingAck] = field(default_factory=dict)
    _session_layer: Optional[SessionLayer] = field(default=None, init=False, repr=False)
    _reconnect_lock: asyncio.Lock = field(default_factory=asyncio.Lock, init=False, repr=False)
    _app_queue: asyncio.Queue[WsEnvelope] = field(default_factory=asyncio.Queue, init=False, repr=False)
    _accept_waiter: Optional[asyncio.Future[None]] = field(default=None, init=False, repr=False)
    _recv_window: Optional[ReceiveWindow[WsEnvelope]] = field(default=None, init=False, repr=False)
    _send_credit: Optional[asyncio.Semaphore] = field(default=None, init=False, repr=False)
    _send_next_seq: int = field(default=1, init=False, repr=False)
    _seq_to_message_id: dict[int, str] = field(default_factory=dict, init=False, repr=False)
    _send_lock: asyncio.Lock = field(default_factory=asyncio.Lock, init=False, repr=False)
    _send_epoch: int = field(default=0, init=False, repr=False)
    _send_waiters: int = field(default=0, init=False, repr=False)

    def _ensure_layer(self) -> None:
        if self._session_layer is None:
            self._session_layer = SessionLayer(
                settings=self.settings,
                build_envelope=self.build_envelope,
                send=self.send,
                concurrency_guard=self.concurrency_guard,
                resource_registry=self.resource_registry,
            )
        else:
            self._session_layer.resource_registry = self.resource_registry

    def _ensure_windows(self) -> None:
        if self._recv_window is None:
            self._recv_window = ReceiveWindow(self.settings.session_window_size)
        if self._send_credit is None:
            self._send_credit = asyncio.Semaphore(self.settings.session_window_size)

    def _reset_windows(self) -> None:
        if self._recv_window:
            self._recv_window.reset()
        old_credit = self._send_credit
        waiters = self._send_waiters
        if old_credit and waiters:
            for _ in range(waiters):
                old_credit.release()
        self._send_credit = asyncio.Semaphore(self.settings.session_window_size)
        self._send_next_seq = 1
        self._seq_to_message_id.clear()
        self._send_epoch += 1

    async def _assign_session_seq(self, message: dict[str, Any]) -> Optional[int]:
        message_type = message.get("type") or ""
        if message_type.startswith("control."):
            return None
        if message.get("session_seq") is not None:
            return message.get("session_seq")
        self._ensure_windows()
        if not self._send_credit:
            return None
        credit = self._send_credit
        epoch = self._send_epoch
        loop = asyncio.get_running_loop()
        start_wait = loop.time()
        self._send_waiters += 1
        try:
            await credit.acquire()
        finally:
            self._send_waiters -= 1
        waited = loop.time() - start_wait
        if waited >= WINDOW_STALL_WARN_SECONDS:
            LOGGER.warning(
                "Send window stalled for %.2fs (pending=%s window=%s)",
                waited,
                len(self._seq_to_message_id),
                self.settings.session_window_size,
            )
        async with self._send_lock:
            if epoch != self._send_epoch:
                credit.release()
                raise SessionResetError("Session reset while waiting for send window")
            seq = self._send_next_seq
            self._send_next_seq += 1
            message["session_seq"] = seq
            message_id = message.get("id") or ""
            self._seq_to_message_id[seq] = message_id
            return seq

    def _release_send_seq(self, seq: Optional[int]) -> None:
        if seq is None:
            return
        message_id = self._seq_to_message_id.pop(seq, None)
        if message_id is None:
            return
        if self._send_credit:
            self._send_credit.release()

    def _apply_window_ack(self, payload: AckPayload) -> None:
        if payload.ack_seq is None:
            return
        window_size = payload.recv_window or self.settings.session_window_size
        for seq in list(self._seq_to_message_id):
            if is_seq_acked(seq, payload.ack_seq, payload.ack_bitmap, window_size):
                self._release_send_seq(seq)

    def _try_transition(self, state: SessionState) -> None:
        try:
            self.session.transition(state)
        except ValueError:
            LOGGER.debug(
                "Ignoring invalid session transition %s -> %s",
                self.session.state.value,
                state.value,
            )

    def next_message_id(self, prefix: str) -> str:
        counter = next(self._message_counter)
        return f"{prefix}-{counter}"

    def build_envelope(
        self,
        message_type: str,
        payload: dict[str, Any] | BaseModel,
        *,
        request_ack: bool = False,
        corr: Optional[str] = None,
        seq: Optional[int] = None,
        session_seq: Optional[int] = None,
    ) -> dict[str, Any]:
        payload_dict = (
            payload.model_dump(exclude_none=True, by_alias=True)
            if isinstance(payload, BaseModel)
            else payload
        )
        envelope = WsEnvelope(
            type=message_type,
            id=self.next_message_id(message_type),
            ts=datetime.now(timezone.utc),
            corr=corr,
            seq=seq,
            session_seq=session_seq,
            tenant=self.settings.tenant,
            sender=Sender(
                role=Role.worker,
                id=self.session.worker_instance_id or self.settings.worker_instance_id or self.settings.worker_name,
            ),
            ack=Ack(request=True) if request_ack else None,
            payload=payload_dict,
        )
        data = envelope.model_dump(by_alias=True, exclude_none=True)
        data["ts"] = envelope.ts.isoformat()
        return data

    async def start(self) -> None:
        """Establish the transport and bring the session to HEARTBEATING."""

        self._ensure_layer()
        self._ensure_windows()
        # ensure we have a stable worker_instance_id before handshake
        if not self.settings.worker_instance_id:
            self.settings.worker_instance_id = self.session.load_or_create_instance_id()
        if not self.session.worker_instance_id:
            self.session.worker_instance_id = self.settings.worker_instance_id
        else:
            self.settings.worker_instance_id = self.session.worker_instance_id
        self._reset_windows()
        self._try_transition(SessionState.NEW)

        if self._manager is None:
            assert self._session_layer is not None
            self._manager = ConnectionManager(
                self.settings,
                self.transport_factory,
                heartbeat_factory=self._session_layer.build_heartbeat_envelope,
                on_disconnect=self._on_transport_disconnect,
                on_reconnect=self._on_transport_reconnect,
            )

        await self._manager.start()
        if self._receive_task is None or self._receive_task.done():
            self._receive_task = asyncio.create_task(self._receive_loop(), name="session-receive")

        await self._establish_session(initial=True)

    async def _establish_session(self, *, initial: bool) -> None:
        assert self._session_layer is not None
        self._prepare_accept_waiter()

        if self.session.session_id and self.session.session_token:
            self._try_transition(SessionState.HANDSHAKING)
            resume_payload = self._session_layer.build_resume_payload(
                session_id=self.session.session_id,
                session_token=self.session.session_token,
                last_seen_seq=None,
            )
            resume_message = self.build_envelope(
                "control.resume",
                resume_payload,
                request_ack=True,
            )
            await self.send_and_wait_ack(resume_message)
        else:
            self._try_transition(SessionState.HANDSHAKING)
            handshake_message = self._session_layer.build_handshake_envelope()
            await self.send_and_wait_ack(handshake_message)

            self._try_transition(SessionState.REGISTERED)
            register_message = self._session_layer.build_register_envelope()
            await self.send_and_wait_ack(register_message)

        await self._wait_for_accept(timeout=float(self.settings.session_accept_timeout_seconds))
        self._try_transition(SessionState.HEARTBEATING)
        if self.on_ready:
            await self._safe_call(self.on_ready, initial)

    async def stop(self) -> None:
        """Close the session and stop background loops."""

        receive_task = self._receive_task
        if receive_task:
            receive_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await receive_task
        self._receive_task = None

        self._cancel_pending_acks()
        self._reject_accept(SessionResetError("session stopped"))
        self.session.session_id = None
        self.session.session_token = None
        self._reset_windows()
        self._try_transition(SessionState.CLOSED)

        if self._manager:
            await self._manager.stop()
        self._manager = None

    async def messages(self) -> AsyncIterator[WsEnvelope]:
        """Yield non-control envelopes after session-level handling."""

        while True:
            envelope = await self._app_queue.get()
            yield envelope

    async def send(self, message: dict[str, Any], *, track_ack: bool = True) -> None:
        """Send a raw envelope dict, tracking ACK if requested."""

        assigned_seq = None
        if message.get("type") and not str(message.get("type")).startswith("control."):
            assigned_seq = await self._assign_session_seq(message)
        ack_request = bool(message.get("ack", {}).get("request"))
        message_id = message.get("id")
        if track_ack and ack_request:
            self._register_ack(message)
        try:
            if not self._manager:
                raise TransportNotReady("Transport has not been initialised")
            await self._manager.send(message)
        except ConnectionError:
            self._release_send_seq(assigned_seq)
            if track_ack and ack_request and message_id:
                self._remove_pending_ack(message_id)
            raise
        except Exception:
            self._release_send_seq(assigned_seq)
            if track_ack and ack_request and message_id:
                self._remove_pending_ack(message_id)
            raise

    async def send_and_wait_ack(self, message: dict[str, Any], *, timeout: Optional[float] = None) -> None:
        """Send a message and await the control.ack response."""

        message_id = message.get("id")
        if not message_id:
            raise ValueError("Cannot wait for ack without message id")
        if not message.get("ack", {}).get("request"):
            raise ValueError("Cannot wait for ack when ack.request is not set")
        if message.get("type") and not str(message.get("type")).startswith("control."):
            await self._assign_session_seq(message)
        future = self._register_ack(message)
        try:
            await self.send(message, track_ack=False)
        except Exception:
            self._remove_pending_ack(message_id)
            raise
        try:
            if timeout:
                await asyncio.wait_for(future, timeout=timeout)
            else:
                await future
        except Exception:
            self._remove_pending_ack(message_id)
            raise

    async def _safe_call(self, fn: Callable[..., Awaitable[None]], *args: Any) -> None:
        try:
            await fn(*args)
        except Exception:  # noqa: BLE001
            LOGGER.debug("Suppress session callback error", exc_info=True)

    def _prepare_accept_waiter(self) -> None:
        if self._accept_waiter and not self._accept_waiter.done():
            self._accept_waiter.cancel()
        self._accept_waiter = asyncio.get_running_loop().create_future()

    async def _wait_for_accept(self, *, timeout: Optional[float] = None) -> None:
        waiter = self._accept_waiter
        if waiter is None:
            raise RuntimeError("Session accept waiter not initialised")
        try:
            if timeout:
                await asyncio.wait_for(waiter, timeout=timeout)
            else:
                await waiter
        except asyncio.TimeoutError as exc:
            raise SessionAcceptTimeout("Timed out waiting for control.session.accept") from exc
        finally:
            if self._accept_waiter is waiter:
                self._accept_waiter = None

    def _resolve_accept(self) -> None:
        if self._accept_waiter and not self._accept_waiter.done():
            self._accept_waiter.set_result(None)

    def _reject_accept(self, exc: Exception) -> None:
        if self._accept_waiter and not self._accept_waiter.done():
            self._accept_waiter.set_exception(exc)

    async def _receive_loop(self) -> None:
        try:
            if not self._manager:
                raise TransportNotReady("Transport has not been initialised")
            async for message in self._manager.messages():
                try:
                    await self._handle_incoming(message)
                except ValidationError as exc:
                    LOGGER.warning("Dropping invalid envelope from scheduler: %s", exc)
                except Exception:  # noqa: BLE001
                    LOGGER.exception("Failed to process inbound envelope")
        except asyncio.CancelledError:
            LOGGER.debug("Session receive loop cancelled")
            raise

    async def _on_transport_disconnect(self, exc: Exception) -> None:
        LOGGER.warning("Transport disconnected: %s", exc)
        self._try_transition(SessionState.BACKOFF)
        if self.on_disconnect:
            await self._safe_call(self.on_disconnect, exc)

    async def _on_transport_reconnect(self) -> None:
        async with self._reconnect_lock:
            LOGGER.info("Transport reconnected; re-establishing session")
            self._ensure_layer()
            self._try_transition(SessionState.NEW)
            try:
                await self._establish_session(initial=False)
            except Exception as exc:  # noqa: BLE001
                LOGGER.error("Failed to re-establish session: %s", exc)
                self._try_transition(SessionState.BACKOFF)
            if self.on_reconnect:
                await self._safe_call(self.on_reconnect)

    async def _handle_incoming(self, message: dict[str, Any]) -> None:
        envelope = WsEnvelope.model_validate(message)

        if envelope.type == "control.ack":
            try:
                ack_payload = AckPayload.model_validate(envelope.payload or {})
            except ValidationError as exc:
                LOGGER.warning("Invalid ack payload: %s", exc)
            else:
                self._apply_window_ack(ack_payload)
            if envelope.ack and envelope.ack.for_:
                LOGGER.debug("Ack received id=%s for=%s", envelope.id, envelope.ack.for_)
                self._resolve_ack(envelope.ack.for_)
            return

        if envelope.type == "control.session.accept":
            accept_payload = SessionAcceptPayload.model_validate(envelope.payload)
            self.session.session_id = accept_payload.session_id
            self.session.session_token = accept_payload.session_token
            self.session.worker_instance_id = accept_payload.worker_instance_id
            if not self.settings.worker_instance_id:
                self.settings.worker_instance_id = accept_payload.worker_instance_id
            if not accept_payload.resumed:
                self._reset_windows()
            self._resolve_accept()
            return

        if envelope.type == "control.reset":
            reset_payload = SessionResetPayload.model_validate(envelope.payload)
            self.session.session_id = None
            self.session.session_token = None
            self._cancel_pending_acks()
            self._reset_windows()
            self._try_transition(SessionState.BACKOFF)
            self._reject_accept(SessionResetError(f"{reset_payload.code}: {reset_payload.reason}"))
            return

        if envelope.type == "control.drain":
            SessionDrainPayload.model_validate(envelope.payload)
            self._try_transition(SessionState.DRAINING)
            return

        if envelope.type.startswith("control."):
            if envelope.ack and envelope.ack.request:
                await self._send_ack(envelope, include_for=True)
            return

        if envelope.session_seq is None:
            if envelope.ack and envelope.ack.request:
                await self._send_ack(envelope, include_for=True)
            await self._app_queue.put(envelope)
            return

        self._ensure_windows()
        assert self._recv_window is not None
        ready, accepted = self._recv_window.record(envelope.session_seq, envelope)
        await self._send_ack(envelope, include_for=bool(envelope.ack and envelope.ack.request))
        if not accepted:
            offset = envelope.session_seq - self._recv_window.base_seq - 1
            if envelope.session_seq in self._recv_window.buffer:
                reason = "duplicate"
            elif offset >= self._recv_window.size:
                reason = "out_of_window"
            elif envelope.session_seq <= self._recv_window.base_seq:
                reason = "stale"
            else:
                reason = "unknown"
            LOGGER.warning(
                "Dropping message seq=%s type=%s reason=%s base_seq=%s window=%s",
                envelope.session_seq,
                envelope.type,
                reason,
                self._recv_window.base_seq,
                self._recv_window.size,
            )
            return
        for ready_envelope in ready:
            await self._app_queue.put(ready_envelope)

    async def _send_ack(self, envelope: WsEnvelope, *, include_for: bool) -> None:
        ack_for = envelope.id if include_for else None
        ack_payload: dict[str, Any] = {"ok": True}
        if ack_for:
            ack_payload["for"] = ack_for
        self._ensure_windows()
        if self._recv_window:
            base_seq, bitmap, window = self._recv_window.ack_state()
            ack_payload["ack_seq"] = base_seq
            ack_payload["ack_bitmap"] = bitmap
            ack_payload["recv_window"] = window
        ack_envelope = self.build_envelope(
            "control.ack",
            payload=ack_payload,
            request_ack=False,
            corr=envelope.corr,
            seq=envelope.seq,
        )
        if ack_for:
            ack_envelope["ack"] = {"for": ack_for}
        await self._send_without_tracking(ack_envelope)

    async def _send_without_tracking(self, message: dict[str, Any]) -> None:
        if not self._manager:
            raise TransportNotReady("Transport has not been initialised")
        await self._manager.send(message)

    def _register_ack(self, message: dict[str, Any]) -> asyncio.Future[None]:
        message_id = message["id"]
        existing = self._pending_acks.get(message_id)
        if existing and existing.future:
            return existing.future
        future = asyncio.get_running_loop().create_future()
        pending = PendingAck(
            message=copy.deepcopy(message),
            future=future,
            session_seq=message.get("session_seq"),
        )
        LOGGER.debug("Tracking ack for message %s", message_id)
        pending.task = asyncio.create_task(self._ack_retry_loop(message_id), name=f"ack-retry-{message_id}")
        self._pending_acks[message_id] = pending
        return future

    async def _ack_retry_loop(self, message_id: str) -> None:
        base_delay = max(self.settings.ack_retry_base_ms / 1000.0, 0.05)
        max_delay = max(self.settings.ack_retry_max_ms / 1000.0, base_delay)
        while True:
            pending = self._pending_acks.get(message_id)
            if not pending:
                return
            if pending.attempts >= self.settings.ack_retry_attempts:
                LOGGER.error("Message %s exceeded ack retries; dropping", message_id)
                self._pending_acks.pop(message_id, None)
                if pending.future and not pending.future.done():
                    pending.future.set_exception(TimeoutError("Ack retry attempts exceeded"))
                return
            delay = min(base_delay * (2**pending.attempts), max_delay)
            await asyncio.sleep(delay)
            if message_id not in self._pending_acks:
                return
            pending = self._pending_acks[message_id]
            try:
                LOGGER.warning("Resending message %s (attempt %s)", message_id, pending.attempts + 1)
                await self._send_without_tracking(pending.message)
            except Exception as exc:  # noqa: BLE001
                LOGGER.exception("Failed to resend message %s: %s", message_id, exc)
                if pending.future and not pending.future.done():
                    pending.future.set_exception(exc)
                self._pending_acks.pop(message_id, None)
                return
            pending.attempts += 1

    def _remove_pending_ack(self, message_id: str) -> None:
        pending = self._pending_acks.pop(message_id, None)
        if pending and pending.task:
            pending.task.cancel()
        if pending:
            self._release_send_seq(pending.session_seq)
        if pending and pending.future and not pending.future.done():
            pending.future.cancel()

    def _resolve_ack(self, message_id: str) -> None:
        pending = self._pending_acks.pop(message_id, None)
        if not pending:
            LOGGER.debug("Received ack for unknown message %s", message_id)
            return
        if pending.task:
            pending.task.cancel()
        self._release_send_seq(pending.session_seq)
        if pending.future and not pending.future.done():
            pending.future.set_result(None)
        LOGGER.info("Ack received for message %s after %s attempts", message_id, pending.attempts)

    def _cancel_pending_acks(self) -> None:
        for pending in self._pending_acks.values():
            if pending.task:
                pending.task.cancel()
            self._release_send_seq(pending.session_seq)
            if pending.future and not pending.future.done():
                pending.future.cancel()
        self._pending_acks.clear()
