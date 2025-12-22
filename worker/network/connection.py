"""Connection wrapper that owns the underlying transport lifecycle."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import random
from typing import Any, AsyncIterator, Awaitable, Callable, Optional

from worker.config import WorkerSettings
from worker.network.transport.base import BaseTransport

LOGGER = logging.getLogger(__name__)


class ConnectionError(RuntimeError):
    """Raised when the transport connection fails."""


class Connection:
    """Maintains a stable connection and exposes message subscription + send."""

    def __init__(
        self,
        settings: WorkerSettings,
        transport_factory: Callable[[WorkerSettings], BaseTransport],
        *,
        heartbeat_factory: Optional[Callable[[], Awaitable[dict]]] = None,
        on_connecting: Optional[Callable[[int], Awaitable[None]]] = None,
        on_connect_failed: Optional[Callable[[int, Exception, float], Awaitable[None]]] = None,
        on_connected: Optional[Callable[[bool, int], Awaitable[None]]] = None,
        on_disconnect: Optional[Callable[[Exception], Awaitable[None]]] = None,
        on_reconnect: Optional[Callable[[], Awaitable[None]]] = None,
        heartbeat_interval: float | None = None,
        heartbeat_jitter: float | None = None,
        base_delay: float | None = None,
        max_delay: float | None = None,
        jitter: float | None = None,
    ) -> None:
        self._settings = settings
        self._transport_factory = transport_factory
        self._transport: Optional[BaseTransport] = None
        self._base_delay = float(base_delay if base_delay is not None else settings.reconnect_base_delay_seconds)
        self._max_delay = float(max_delay if max_delay is not None else settings.reconnect_max_delay_seconds)
        self._jitter = float(jitter if jitter is not None else settings.reconnect_jitter)
        queue_max = int(settings.transport_recv_queue_max or 0)
        if queue_max < 0:
            queue_max = 0
        self._recv_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=queue_max)
        self._recv_task: Optional[asyncio.Task[None]] = None
        self._heartbeat_task: Optional[asyncio.Task[None]] = None
        self._connect_task: Optional[asyncio.Task[None]] = None
        self._heartbeat_factory = heartbeat_factory
        self._on_connecting = on_connecting
        self._on_connect_failed = on_connect_failed
        self._on_connected = on_connected
        self._on_disconnect = on_disconnect
        self._on_reconnect = on_reconnect
        self._heartbeat_interval = float(
            heartbeat_interval if heartbeat_interval is not None else settings.heartbeat_interval_seconds
        )
        self._heartbeat_jitter = float(
            heartbeat_jitter if heartbeat_jitter is not None else settings.heartbeat_jitter_seconds
        )
        self._stopped = asyncio.Event()
        self._ever_connected = False
        self._last_error_type: Optional[str] = None

    async def start(self) -> None:
        """Ensure connection and start receive/heartbeat loops."""

        if self._recv_task and not self._recv_task.done():
            return
        self._stopped.clear()
        await self._ensure_connected()
        self._recv_task = asyncio.create_task(self._receive_loop(), name="transport-recv")
        if self._heartbeat_factory and self._heartbeat_interval:
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop(), name="transport-heartbeat")

    async def stop(self) -> None:
        """Close the transport and stop background loops."""

        self._stopped.set()
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._heartbeat_task
        if self._recv_task:
            self._recv_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._recv_task
        if self._connect_task:
            self._connect_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._connect_task
        if self._transport:
            await self._transport.close()
        self._transport = None
        self._recv_task = None
        self._heartbeat_task = None
        self._connect_task = None

    async def send(self, message: dict) -> None:
        """Send a message immediately, reconnecting on failure."""

        await self.start()
        if not self._transport:
            raise ConnectionError("Transport not available")
        try:
            await self._transport.send(message)
        except Exception as exc:  # noqa: BLE001
            await self._handle_transport_error(exc)

    async def messages(self) -> AsyncIterator[dict[str, Any]]:
        """Async iterator of inbound raw envelopes (dicts)."""

        await self.start()
        while not self._stopped.is_set():
            message = await self._recv_queue.get()
            yield message

    def recv_queue_size(self) -> int:
        return self._recv_queue.qsize()

    def last_error_type(self) -> Optional[str]:
        return self._last_error_type

    def _classify_error(self, exc: Exception) -> str:
        status_code = getattr(exc, "status_code", None)
        if status_code is None:
            status_code = getattr(exc, "code", None)
        if status_code in {401, 403}:
            return "auth"
        if status_code in {400, 404, 426}:
            return "protocol"
        message = str(exc).lower()
        if any(token in message for token in ("unauthorized", "forbidden", "invalid token", "auth")):
            return "auth"
        if any(token in message for token in ("protocol", "handshake", "invalid status", "unsupported")):
            return "protocol"
        if any(token in message for token in ("timeout", "timed out", "refused", "unreachable", "reset")):
            return "network"
        return "unknown"

    def _is_fatal_error(self, error_type: str) -> bool:
        if error_type == "auth" and self._settings.reconnect_abort_on_auth_error:
            return True
        if error_type == "protocol" and self._settings.reconnect_abort_on_protocol_error:
            return True
        return False

    async def _handle_transport_error(self, exc: Exception, *, rethrow: bool = True) -> None:
        error_type = self._classify_error(exc)
        self._last_error_type = error_type
        LOGGER.warning("Transport error encountered, will reconnect: %s", exc)
        if self._stopped.is_set():
            if rethrow:
                raise ConnectionError("Transport connection stopped") from exc
            return
        if self._on_disconnect:
            try:
                await self._on_disconnect(exc)
            except Exception:  # noqa: BLE001
                LOGGER.debug("Suppress transport disconnect callback error", exc_info=True)
        if self._transport:
            try:
                await self._transport.close()
            except Exception:  # noqa: BLE001
                LOGGER.debug("Suppress transport close error", exc_info=True)
        self._transport = None
        if self._is_fatal_error(error_type):
            self._stopped.set()
            raise ConnectionError(f"Fatal transport error ({error_type})") from exc
        await self._ensure_connected()
        if self._on_reconnect:
            try:
                task = asyncio.create_task(self._on_reconnect(), name="transport-on-reconnect")
                task.add_done_callback(lambda t: LOGGER.debug("Transport reconnect callback failed", exc_info=t.exception()) if t.exception() else None)
            except Exception:  # noqa: BLE001
                LOGGER.debug("Suppress transport reconnect callback error", exc_info=True)
        if rethrow:
            raise ConnectionError(str(exc)) from exc

    async def _ensure_connected(self) -> None:
        if self._transport:
            return
        if self._stopped.is_set():
            raise ConnectionError("Transport connection stopped")
        task = self._connect_task
        if task and not task.done():
            await task
            return
        self._connect_task = asyncio.create_task(self._connect_with_backoff(), name="transport-connect")
        try:
            await self._connect_task
        finally:
            if self._connect_task and self._connect_task.done():
                self._connect_task = None

    async def _connect_with_backoff(self) -> None:
        attempt = 0
        while not self._stopped.is_set():
            try:
                attempt += 1
                if self._on_connecting:
                    try:
                        await self._on_connecting(attempt)
                    except Exception:  # noqa: BLE001
                        LOGGER.debug("Suppress transport on_connecting callback error", exc_info=True)
                transport = self._transport_factory(self._settings)
                await transport.connect()
                self._transport = transport
                initial = not self._ever_connected
                self._ever_connected = True
                self._last_error_type = None
                LOGGER.info("Transport connected after %s attempt(s)", attempt)
                if self._on_connected:
                    try:
                        await self._on_connected(initial, attempt)
                    except Exception:  # noqa: BLE001
                        LOGGER.debug("Suppress transport on_connected callback error", exc_info=True)
                return
            except Exception as exc:  # noqa: BLE001
                error_type = self._classify_error(exc)
                self._last_error_type = error_type
                if self._is_fatal_error(error_type):
                    self._stopped.set()
                    raise ConnectionError(f"Fatal transport error ({error_type})") from exc
                if self._stopped.is_set():
                    raise ConnectionError("Transport connection stopped") from exc
                delay = min(self._max_delay, self._base_delay * (2 ** (attempt - 1)))
                jitter_factor = random.uniform(1 - self._jitter, 1 + self._jitter)
                sleep_for = max(0.1, delay * jitter_factor)
                if self._on_connect_failed:
                    try:
                        await self._on_connect_failed(attempt, exc, sleep_for)
                    except Exception:  # noqa: BLE001
                        LOGGER.debug("Suppress transport on_connect_failed callback error", exc_info=True)
                LOGGER.warning("Transport connect failed (attempt %s): %s; retrying in %.2fs", attempt, exc, sleep_for)
                await asyncio.sleep(sleep_for)
        raise ConnectionError("Transport connection stopped")

    async def _receive_loop(self) -> None:
        while not self._stopped.is_set():
            try:
                if not self._transport:
                    await self._ensure_connected()
                raw = await self._transport.receive()  # type: ignore[union-attr]
                await self._recv_queue.put(raw)
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001
                LOGGER.warning("Receive loop error, reconnecting: %s", exc)
                await self._handle_transport_error(exc, rethrow=False)

    async def _heartbeat_loop(self) -> None:
        assert self._heartbeat_factory is not None
        assert self._heartbeat_interval is not None
        while not self._stopped.is_set():
            interval = float(self._heartbeat_interval)
            if self._heartbeat_jitter:
                interval += random.uniform(0, self._heartbeat_jitter)
            try:
                await asyncio.sleep(interval)
                payload = await self._heartbeat_factory()
                await self.send(payload)
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001
                LOGGER.warning("Heartbeat loop error: %s", exc)
                await asyncio.sleep(min(self._max_delay, interval))
