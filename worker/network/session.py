"""Pure session layer for the worker control-plane connection.

This layer is responsible for:
- Transport lifecycle (via Connection)
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
import shutil
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

from worker.execution.runtime import ConcurrencyGuard, ResourceRegistry
from worker.config import WorkerSettings
from worker.network.session_state import SessionState, SessionTracker
from worker.network.session_layer import SessionLayer
from worker.network.connection import ConnectionError, Connection
from worker.network.transport.base import BaseTransport

LOGGER = logging.getLogger(__name__)
WINDOW_STALL_WARN_SECONDS = 1.0

try:
    import psutil  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    psutil = None


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
    future: Optional[asyncio.Future[None]] = None
    session_seq: Optional[int] = None
    next_retry_at: float = 0.0


@dataclass
class PendingWindow:
    message: dict[str, Any]
    attempts: int = 0
    session_seq: int = 0
    next_retry_at: float = 0.0


@dataclass
class Session:
    """Worker-side session client for the scheduler control-plane."""

    settings: WorkerSettings
    transport_factory: Callable[[WorkerSettings], BaseTransport]
    concurrency_guard: ConcurrencyGuard = field(default_factory=ConcurrencyGuard)
    resource_registry: Optional[ResourceRegistry] = None
    package_inventory: list[dict[str, Any]] = field(default_factory=list)
    package_manifests: list[dict[str, Any]] = field(default_factory=list)
    session: SessionTracker = field(default_factory=SessionTracker)
    on_connecting: Optional[Callable[[int], Awaitable[None]]] = None
    on_connect_failed: Optional[Callable[[int, Exception, float], Awaitable[None]]] = None
    on_connected: Optional[Callable[[bool, int], Awaitable[None]]] = None
    on_disconnect: Optional[Callable[[Exception], Awaitable[None]]] = None
    on_reconnect: Optional[Callable[[], Awaitable[None]]] = None
    on_ready: Optional[Callable[[bool], Awaitable[None]]] = None

    _conn: Optional[Connection] = None
    _receive_task: Optional[asyncio.Task[None]] = None
    _message_counter: Iterator[int] = field(default_factory=lambda: count())
    _pending_acks: dict[str, PendingAck] = field(default_factory=dict)
    _pending_window: dict[int, PendingWindow] = field(default_factory=dict, init=False, repr=False)
    _session_layer: Optional[SessionLayer] = field(default=None, init=False, repr=False)
    _reconnect_lock: asyncio.Lock = field(default_factory=asyncio.Lock, init=False, repr=False)
    _accept_waiter: Optional[asyncio.Future[None]] = field(default=None, init=False, repr=False)
    _recv_window: Optional[ReceiveWindow[WsEnvelope]] = field(default=None, init=False, repr=False)
    _send_credit: Optional[asyncio.Semaphore] = field(default=None, init=False, repr=False)
    _send_next_seq: int = field(default=1, init=False, repr=False)
    _seq_to_message_id: dict[int, str] = field(default_factory=dict, init=False, repr=False)
    _send_lock: asyncio.Lock = field(default_factory=asyncio.Lock, init=False, repr=False)
    _send_epoch: int = field(default=0, init=False, repr=False)
    _send_waiters: int = field(default=0, init=False, repr=False)
    _force_fresh_session: bool = field(default=False, init=False, repr=False)
    _ack_retry_task: Optional[asyncio.Task[None]] = field(default=None, init=False, repr=False)
    _ack_retry_event: asyncio.Event = field(default_factory=asyncio.Event, init=False, repr=False)
    _app_queue: asyncio.Queue[WsEnvelope] = field(init=False, repr=False)
    _app_queue_overflow: str = field(default="block", init=False, repr=False)
    _app_queue_drops: int = field(default=0, init=False, repr=False)
    _last_recv_at: Optional[float] = field(default=None, init=False, repr=False)
    _last_send_at: Optional[float] = field(default=None, init=False, repr=False)
    _last_ack_at: Optional[float] = field(default=None, init=False, repr=False)
    _conn_state: str = field(default="idle", init=False, repr=False)

    def __post_init__(self) -> None:
        queue_max = int(self.settings.session_app_queue_max or 0)
        if queue_max < 0:
            queue_max = 0
        self._app_queue = asyncio.Queue(maxsize=queue_max)
        overflow = getattr(self.settings, "session_app_queue_overflow", "block")
        if overflow not in {"block", "drop_new", "drop_oldest"}:
            overflow = "block"
        self._app_queue_overflow = overflow

    def _ensure_layer(self) -> None:
        if self._session_layer is None:
            self._session_layer = SessionLayer(
                settings=self.settings,
                build_envelope=self.build_envelope,
                send=self.send,
                concurrency_guard=self.concurrency_guard,
                resource_registry=self.resource_registry,
                metrics_provider=self._collect_metrics,
                package_inventory=self.package_inventory,
                package_manifests=self.package_manifests,
            )
        else:
            self._session_layer.resource_registry = self.resource_registry
            self._session_layer.package_inventory = self.package_inventory
            self._session_layer.package_manifests = self.package_manifests

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
        self._pending_window.clear()
        self._send_epoch += 1
        self._ack_retry_event.set()

    def _collect_metrics(self) -> dict[str, Any]:
        metrics = {
            "pending_acks": len(self._pending_acks),
            "app_queue": self._app_queue.qsize(),
            "app_queue_drops": self._app_queue_drops,
            "conn_state": self._conn_state,
            "send_inflight": len(self._seq_to_message_id),
            "send_waiters": self._send_waiters,
        }
        data_dir = self.settings.data_dir
        if psutil:
            try:
                metrics["cpu_pct"] = float(psutil.cpu_percent(interval=None))
                metrics["mem_pct"] = float(psutil.virtual_memory().percent)
                metrics["disk_pct"] = float(psutil.disk_usage(str(data_dir)).percent)
            except Exception:  # noqa: BLE001
                LOGGER.debug("Suppress system metrics error", exc_info=True)
        else:
            try:
                usage = shutil.disk_usage(data_dir)
                if usage.total > 0:
                    metrics["disk_pct"] = (usage.used / usage.total) * 100
            except Exception:  # noqa: BLE001
                LOGGER.debug("Suppress disk metrics error", exc_info=True)
        try:
            now = asyncio.get_running_loop().time()
        except RuntimeError:
            now = None
        if now is not None:
            if self._last_recv_at is not None:
                metrics["last_recv_ms"] = int((now - self._last_recv_at) * 1000)
            if self._last_send_at is not None:
                metrics["last_send_ms"] = int((now - self._last_send_at) * 1000)
            if self._last_ack_at is not None:
                metrics["last_ack_ms"] = int((now - self._last_ack_at) * 1000)
        if self._conn:
            metrics["recv_queue"] = self._conn.recv_queue_size()
            if self._conn.last_error_type():
                metrics["conn_error"] = self._conn.last_error_type()
        if self._recv_window:
            metrics["recv_base_seq"] = self._recv_window.base_seq
            metrics["recv_buffer"] = len(self._recv_window.buffer)
        return metrics

    def _mark_recv(self) -> None:
        self._last_recv_at = asyncio.get_running_loop().time()

    def _mark_send(self) -> None:
        self._last_send_at = asyncio.get_running_loop().time()

    def _mark_ack(self) -> None:
        self._last_ack_at = asyncio.get_running_loop().time()

    async def _enqueue_app(self, envelope: WsEnvelope) -> None:
        if not self._app_queue.full() or self._app_queue_overflow == "block":
            await self._app_queue.put(envelope)
            return
        if self._app_queue_overflow == "drop_new":
            self._app_queue_drops += 1
            LOGGER.warning("App queue full; dropping message type=%s id=%s", envelope.type, envelope.id)
            return
        if self._app_queue_overflow == "drop_oldest":
            try:
                dropped = self._app_queue.get_nowait()
            except asyncio.QueueEmpty:
                dropped = None
            else:
                self._app_queue_drops += 1
                LOGGER.warning(
                    "App queue full; dropping oldest message type=%s id=%s",
                    dropped.type,
                    dropped.id,
                )
            await self._app_queue.put(envelope)

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
        removed = self._pending_window.pop(seq, None)
        if removed:
            self._ack_retry_event.set()
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
                message_id = self._seq_to_message_id.get(seq)
                self._release_send_seq(seq)
                if message_id and message_id in self._pending_acks:
                    self._resolve_ack(message_id)

    def _try_transition(self, state: SessionState) -> None:
        try:
            self.session.transition(state)
        except ValueError:
            LOGGER.debug(
                "Ignoring invalid session transition %s -> %s",
                self.session.state.value,
                state.value,
            )

    async def _restart_after_reset(self) -> None:
        """Stop and restart the connection after a control.reset."""

        try:
            if self._receive_task:
                self._receive_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await self._receive_task
                self._receive_task = None
            if self._conn:
                await self._conn.stop()
                self._conn = None
            # ensure accept waiter reset and windows clean
            self._cancel_pending_acks()
            self._reset_windows()
            self._try_transition(SessionState.NEW)
            await self.start()
        except Exception as exc:  # noqa: BLE001
            LOGGER.error("Failed to restart session after reset: %s", exc)

    def _mark_session_stale(self, reason: str) -> None:
        """Force the next connection to perform a full handshake/register."""

        self.session.session_id = None
        self.session.session_token = None
        self._force_fresh_session = True
        self._cancel_pending_acks()
        self._reset_windows()
        self._reject_accept(SessionResetError(reason))

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

        if self._conn is None:
            assert self._session_layer is not None
            self._conn = Connection(
                self.settings,
                self.transport_factory,
                heartbeat_factory=self._session_layer.build_heartbeat_envelope,
                on_connecting=self._on_transport_connecting,
                on_connect_failed=self._on_transport_connect_failed,
                on_connected=self._on_transport_connected,
                on_disconnect=self._on_transport_disconnect,
                on_reconnect=self._on_transport_reconnect,
            )

        await self._conn.start()
        if self._receive_task is None or self._receive_task.done():
            self._receive_task = asyncio.create_task(self._receive_loop(), name="session-receive")

        await self._establish_session(initial=True)

    async def _establish_session(self, *, initial: bool) -> None:
        assert self._session_layer is not None
        self._prepare_accept_waiter()

        if not self._force_fresh_session and self.session.session_id and self.session.session_token:
            self._try_transition(SessionState.HANDSHAKING)
            last_seen_seq = None
            if self._recv_window:
                last_seen_seq = self._recv_window.base_seq
            resume_payload = self._session_layer.build_resume_payload(
                session_id=self.session.session_id,
                session_token=self.session.session_token,
                last_seen_seq=last_seen_seq,
            )
            resume_message = self.build_envelope(
                "control.resume",
                resume_payload,
                request_ack=True,
            )
            try:
                await self.send_and_wait_ack(resume_message)
                await self._wait_for_accept(timeout=float(self.settings.session_accept_timeout_seconds))
            except ConnectionError as exc:
                self._mark_session_stale(str(exc))
                raise
            except (SessionAcceptTimeout, TimeoutError) as exc:
                LOGGER.warning("Resume failed (%s); falling back to full handshake", exc)
                self._mark_session_stale(str(exc))
                self._prepare_accept_waiter()
            else:
                self._try_transition(SessionState.HEARTBEATING)
                self._force_fresh_session = False
                if self.on_ready:
                    await self._safe_call(self.on_ready, initial)
                return

        self._try_transition(SessionState.HANDSHAKING)
        handshake_message = self._session_layer.build_handshake_envelope()
        await self.send_and_wait_ack(handshake_message)

        self._try_transition(SessionState.REGISTERED)
        register_message = self._session_layer.build_register_envelope()
        await self.send_and_wait_ack(register_message)

        await self._wait_for_accept(timeout=float(self.settings.session_accept_timeout_seconds))
        self._try_transition(SessionState.HEARTBEATING)
        self._force_fresh_session = False
        if self.on_ready:
            await self._safe_call(self.on_ready, initial)

    async def stop(self) -> None:
        """Close the session and stop background loops."""

        self._conn_state = "stopped"
        receive_task = self._receive_task
        if receive_task:
            receive_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await receive_task
        self._receive_task = None

        self._cancel_pending_acks()
        if self._ack_retry_task:
            self._ack_retry_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._ack_retry_task
        self._ack_retry_task = None
        self._reject_accept(SessionResetError("session stopped"))
        self.session.session_id = None
        self.session.session_token = None
        self._reset_windows()
        self._try_transition(SessionState.CLOSED)

        if self._conn:
            await self._conn.stop()
        self._conn = None

    async def messages(self) -> AsyncIterator[WsEnvelope]:
        """Yield non-control envelopes after session-level handling."""

        while True:
            envelope = await self._app_queue.get()
            yield envelope

    async def refresh_registration(self) -> None:
        """Send an updated control.register payload without waiting for session.accept."""

        self._ensure_layer()
        if self.session.state not in {SessionState.REGISTERED, SessionState.HEARTBEATING}:
            raise SessionResetError("Session not ready for registration refresh")
        assert self._session_layer is not None
        message = self._session_layer.build_register_envelope()
        await self.send_and_wait_ack(message)

    async def send(self, message: dict[str, Any], *, track_ack: bool = True) -> None:
        """Send a raw envelope dict, tracking ACK if requested."""

        assigned_seq = None
        existing_seq = message.get("session_seq")
        if message.get("type") and not str(message.get("type")).startswith("control."):
            assigned_seq = await self._assign_session_seq(message)
        ack_request = bool(message.get("ack", {}).get("request"))
        if assigned_seq is not None and not ack_request and existing_seq is None:
            self._register_window(message, assigned_seq)
        message_id = message.get("id")
        if track_ack and ack_request:
            self._register_ack(message)
        try:
            if not self._conn:
                raise TransportNotReady("Transport has not been initialised")
            await self._conn.send(message)
            self._mark_send()
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
            if not self._conn:
                raise TransportNotReady("Transport has not been initialised")
            async for message in self._conn.messages():
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
        reason = str(exc)
        if "service restart" in reason or "Unknown session" in reason or "1012" in reason:
            self._mark_session_stale(reason)
        self._conn_state = "backoff"
        self._try_transition(SessionState.BACKOFF)
        if self.on_disconnect:
            await self._safe_call(self.on_disconnect, exc)

    async def _on_transport_connecting(self, attempt: int) -> None:
        self._conn_state = "connecting"
        if self.on_connecting:
            await self._safe_call(self.on_connecting, attempt)

    async def _on_transport_connect_failed(self, attempt: int, exc: Exception, delay: float) -> None:
        self._conn_state = "backoff"
        if self.on_connect_failed:
            await self._safe_call(self.on_connect_failed, attempt, exc, delay)

    async def _on_transport_connected(self, initial: bool, attempt: int) -> None:
        self._conn_state = "connected"
        if self.on_connected:
            await self._safe_call(self.on_connected, initial, attempt)

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
        self._mark_recv()

        if envelope.type == "control.ack":
            ack_for: Optional[str] = None
            ack_payload: Optional[AckPayload] = None
            try:
                ack_payload = AckPayload.model_validate(envelope.payload or {})
            except ValidationError as exc:
                LOGGER.warning("Invalid ack payload: %s", exc)
            else:
                self._apply_window_ack(ack_payload)
            if envelope.ack and envelope.ack.for_:
                ack_for = envelope.ack.for_
            elif ack_payload and ack_payload.for_:
                # Fallback for peers that only echo the ack target in payload.
                ack_for = ack_payload.for_
            if ack_for:
                LOGGER.debug("Ack received id=%s for=%s", envelope.id, ack_for)
                self._resolve_ack(ack_for)
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
            self._mark_session_stale(f"{reset_payload.code}: {reset_payload.reason}")
            self._try_transition(SessionState.BACKOFF)
            # Attempt to re-establish a fresh session on reset by restarting transport/session.
            asyncio.create_task(self._restart_after_reset(), name="session-restart-after-reset")
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
            await self._enqueue_app(envelope)
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
            await self._enqueue_app(ready_envelope)

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
        if not self._conn:
            raise TransportNotReady("Transport has not been initialised")
        await self._conn.send(message)
        self._mark_send()

    def _register_window(self, message: dict[str, Any], session_seq: int) -> None:
        if session_seq in self._pending_window:
            return
        loop = asyncio.get_running_loop()
        base_delay = max(self.settings.ack_retry_base_ms / 1000.0, 0.05)
        pending = PendingWindow(
            message=copy.deepcopy(message),
            session_seq=session_seq,
            next_retry_at=loop.time() + base_delay,
        )
        self._pending_window[session_seq] = pending
        self._ensure_ack_retry_task()
        self._ack_retry_event.set()

    def _register_ack(self, message: dict[str, Any]) -> asyncio.Future[None]:
        message_id = message["id"]
        existing = self._pending_acks.get(message_id)
        if existing and existing.future:
            return existing.future
        loop = asyncio.get_running_loop()
        base_delay = max(self.settings.ack_retry_base_ms / 1000.0, 0.05)
        future = asyncio.get_running_loop().create_future()
        pending = PendingAck(
            message=copy.deepcopy(message),
            future=future,
            session_seq=message.get("session_seq"),
            next_retry_at=loop.time() + base_delay,
        )
        LOGGER.debug("Tracking ack for message %s", message_id)
        self._pending_acks[message_id] = pending
        self._ensure_ack_retry_task()
        self._ack_retry_event.set()
        return future

    def _ensure_ack_retry_task(self) -> None:
        if self._ack_retry_task and not self._ack_retry_task.done():
            return
        self._ack_retry_task = asyncio.create_task(self._ack_retry_scheduler(), name="ack-retry")

    async def _ack_retry_scheduler(self) -> None:
        base_delay = max(self.settings.ack_retry_base_ms / 1000.0, 0.05)
        max_delay = max(self.settings.ack_retry_max_ms / 1000.0, base_delay)
        while True:
            try:
                if not self._pending_acks and not self._pending_window:
                    await self._ack_retry_event.wait()
                    self._ack_retry_event.clear()
                    continue

                loop = asyncio.get_running_loop()
                next_retry_at = None
                for pending in self._pending_acks.values():
                    if next_retry_at is None or pending.next_retry_at < next_retry_at:
                        next_retry_at = pending.next_retry_at
                for pending in self._pending_window.values():
                    if next_retry_at is None or pending.next_retry_at < next_retry_at:
                        next_retry_at = pending.next_retry_at

                if next_retry_at is None:
                    await self._ack_retry_event.wait()
                    self._ack_retry_event.clear()
                    continue

                delay = max(0.0, next_retry_at - loop.time())
                try:
                    await asyncio.wait_for(self._ack_retry_event.wait(), timeout=delay)
                    self._ack_retry_event.clear()
                    continue
                except asyncio.TimeoutError:
                    pass

                now = loop.time()
                due_ids = [
                    message_id
                    for message_id, pending in self._pending_acks.items()
                    if pending.next_retry_at <= now
                ]
                for message_id in due_ids:
                    pending = self._pending_acks.get(message_id)
                    if not pending:
                        continue
                    if pending.attempts >= self.settings.ack_retry_attempts:
                        LOGGER.error("Message %s exceeded ack retries; dropping", message_id)
                        self._pending_acks.pop(message_id, None)
                        self._release_send_seq(pending.session_seq)
                        if pending.future and not pending.future.done():
                            pending.future.set_exception(TimeoutError("Ack retry attempts exceeded"))
                        continue
                    try:
                        LOGGER.warning("Resending message %s (attempt %s)", message_id, pending.attempts + 1)
                        await self._send_without_tracking(pending.message)
                    except Exception as exc:  # noqa: BLE001
                        LOGGER.exception("Failed to resend message %s: %s", message_id, exc)
                        self._release_send_seq(pending.session_seq)
                        if pending.future and not pending.future.done():
                            pending.future.set_exception(exc)
                        self._pending_acks.pop(message_id, None)
                        continue
                    pending.attempts += 1
                    next_delay = min(base_delay * (2**pending.attempts), max_delay)
                    pending.next_retry_at = loop.time() + next_delay

                due_seqs = [
                    seq
                    for seq, pending in self._pending_window.items()
                    if pending.next_retry_at <= now
                ]
                for seq in due_seqs:
                    pending = self._pending_window.get(seq)
                    if not pending:
                        continue
                    if pending.attempts >= self.settings.ack_retry_attempts:
                        LOGGER.error("Message seq=%s exceeded ack retries; dropping", seq)
                        self._pending_window.pop(seq, None)
                        self._release_send_seq(seq)
                        continue
                    try:
                        LOGGER.warning(
                            "Resending message seq=%s id=%s (attempt %s)",
                            seq,
                            pending.message.get("id"),
                            pending.attempts + 1,
                        )
                        await self._send_without_tracking(pending.message)
                    except Exception as exc:  # noqa: BLE001
                        LOGGER.exception("Failed to resend message seq=%s: %s", seq, exc)
                        pending.attempts += 1
                        if pending.attempts >= self.settings.ack_retry_attempts:
                            LOGGER.error("Message seq=%s exceeded ack retries; dropping", seq)
                            self._pending_window.pop(seq, None)
                            self._release_send_seq(seq)
                            continue
                        next_delay = min(base_delay * (2**pending.attempts), max_delay)
                        pending.next_retry_at = loop.time() + next_delay
                        continue
                    pending.attempts += 1
                    next_delay = min(base_delay * (2**pending.attempts), max_delay)
                    pending.next_retry_at = loop.time() + next_delay
            except asyncio.CancelledError:
                raise
            except Exception:  # noqa: BLE001
                LOGGER.exception("Ack retry scheduler crashed")

    def _remove_pending_ack(self, message_id: str) -> None:
        pending = self._pending_acks.pop(message_id, None)
        if pending:
            self._release_send_seq(pending.session_seq)
        if pending and pending.future and not pending.future.done():
            pending.future.cancel()
        if pending:
            self._ack_retry_event.set()

    def _resolve_ack(self, message_id: str) -> None:
        pending = self._pending_acks.pop(message_id, None)
        if not pending:
            LOGGER.debug("Received ack for unknown message %s", message_id)
            return
        self._release_send_seq(pending.session_seq)
        if pending.future and not pending.future.done():
            pending.future.set_result(None)
        self._mark_ack()
        LOGGER.info("Ack received for message %s after %s attempts", message_id, pending.attempts)
        self._ack_retry_event.set()

    def _cancel_pending_acks(self) -> None:
        for pending in self._pending_acks.values():
            self._release_send_seq(pending.session_seq)
            if pending.future and not pending.future.done():
                pending.future.cancel()
        self._pending_acks.clear()
        self._ack_retry_event.set()
