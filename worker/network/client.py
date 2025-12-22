"""Network client facade for the worker (session + biz routing)."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import inspect
from collections import defaultdict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, Optional, List, Dict

from worker.execution.runtime import ConcurrencyGuard
from worker.packages import AdapterRegistry, PackageManager
from worker.execution.runtime import ResourceRegistry
from worker.execution import Runner
from worker.config import WorkerSettings
from worker.network.session import Session
from worker.network.transport.base import BaseTransport
from shared.models.session import WsEnvelope

LOGGER = logging.getLogger(__name__)

Handler = Callable[[WsEnvelope], Awaitable[None]]


@dataclass
class NetworkClient:
    """Wires the session + biz layers and routes inbound application frames."""

    settings: WorkerSettings
    transport_factory: Callable[[WorkerSettings], BaseTransport]
    package_handler: Optional[Callable[[str, dict[str, Any]], Awaitable[None]]] = None
    adapter_registry: Optional[AdapterRegistry] = None
    runner: Optional[Runner] = None
    package_manager: Optional[PackageManager] = None
    resource_registry: Optional[ResourceRegistry] = None
    package_inventory: list[dict[str, Any]] = field(default_factory=list)
    package_manifests: list[dict[str, Any]] = field(default_factory=list)
    concurrency_guard: ConcurrencyGuard = field(default_factory=ConcurrencyGuard)

    session: Optional[Session] = field(default=None, init=False, repr=False)
    biz: Any = field(default=None, init=False, repr=False)
    _route_task: Optional[asyncio.Task[None]] = field(default=None, init=False, repr=False)
    _handlers: Dict[str, List[Handler]] = field(default_factory=lambda: defaultdict(list), init=False, repr=False)
    _dispatch_semaphore: Optional[asyncio.Semaphore] = field(default=None, init=False, repr=False)
    _dispatch_queue_max: int = field(default=0, init=False, repr=False)
    _dispatch_queue_overflow: str = field(default="block", init=False, repr=False)
    _dispatch_timeout: float = field(default=0, init=False, repr=False)
    _dispatch_failure_limit: int = field(default=0, init=False, repr=False)
    _dispatch_failure_cooldown: float = field(default=0, init=False, repr=False)
    _handler_failures: Dict[tuple[str, Handler], int] = field(default_factory=dict, init=False, repr=False)
    _handler_backoff_until: Dict[tuple[str, Handler], float] = field(default_factory=dict, init=False, repr=False)
    _type_idle_seconds: float = field(default=0, init=False, repr=False)
    _type_gc_interval: float = field(default=0, init=False, repr=False)
    _type_queues: Dict[str, asyncio.Queue[WsEnvelope]] = field(default_factory=dict, init=False, repr=False)
    _type_tasks: Dict[str, asyncio.Task[None]] = field(default_factory=dict, init=False, repr=False)
    _type_last_activity: Dict[str, float] = field(default_factory=dict, init=False, repr=False)
    _type_busy: Dict[str, int] = field(default_factory=dict, init=False, repr=False)
    _type_gc_task: Optional[asyncio.Task[None]] = field(default=None, init=False, repr=False)
    _disconnect_hooks: List[Callable[[Exception], Awaitable[None] | None]] = field(
        default_factory=list, init=False, repr=False
    )
    _stop_hooks: List[Callable[[], Awaitable[None] | None]] = field(default_factory=list, init=False, repr=False)

    def _ensure_layers(self) -> None:
        if self.session is None:
            self.session = Session(
                settings=self.settings,
                transport_factory=self.transport_factory,
                concurrency_guard=self.concurrency_guard,
                resource_registry=self.resource_registry,
                on_disconnect=self._on_session_disconnect,
            )
        else:
            self.session.resource_registry = self.resource_registry
        self.session.package_inventory = self.package_inventory
        self.session.package_manifests = self.package_manifests

    async def start(self) -> None:
        self._ensure_layers()
        self._ensure_dispatch_control()
        self._ensure_type_gc()
        assert self.session is not None
        await self.session.start()
        if self._route_task is None or self._route_task.done():
            self._route_task = asyncio.create_task(self._route_loop(), name="biz-router")

    async def stop(self) -> None:
        route_task = self._route_task
        if route_task:
            route_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await route_task
        self._route_task = None

        await self._stop_type_tasks()
        await self._stop_type_gc()
        self._dispatch_semaphore = None
        await self._run_hooks(self._stop_hooks)
        self._ensure_layers()
        if self.session is not None:
            await self.session.stop()

    async def refresh_registration(self) -> None:
        """Re-send control.register with updated capability/package metadata."""

        self._ensure_layers()
        if self.package_manager:
            inventory, manifests = self.package_manager.collect_inventory()
            self.package_inventory = inventory
            self.package_manifests = manifests
            if self.session is not None:
                self.session.package_inventory = inventory
                self.session.package_manifests = manifests
        if self.session is None:
            raise RuntimeError("Session not initialised")
        await self.session.refresh_registration()

    async def _route_loop(self) -> None:
        assert self.session is not None
        try:
            async for envelope in self.session.messages():
                await self._enqueue_type(envelope.type, envelope)
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001
            LOGGER.exception("Business routing loop crashed")
            await self._run_hooks(self._disconnect_hooks, RuntimeError("router crashed"))

    def _ensure_dispatch_control(self) -> None:
        if self._dispatch_semaphore is not None:
            return
        limit = int(self.settings.dispatch_max_inflight or 0)
        if limit > 0:
            self._dispatch_semaphore = asyncio.Semaphore(limit)
        self._dispatch_queue_max = max(0, int(self.settings.dispatch_queue_max or 0))
        overflow = self.settings.dispatch_queue_overflow
        if overflow not in {"block", "drop_new", "drop_oldest"}:
            overflow = "block"
        self._dispatch_queue_overflow = overflow
        self._dispatch_timeout = float(self.settings.dispatch_timeout_seconds or 0)
        self._dispatch_failure_limit = int(self.settings.dispatch_max_failures or 0)
        self._dispatch_failure_cooldown = float(self.settings.dispatch_failure_cooldown_seconds or 0)
        self._type_idle_seconds = float(self.settings.dispatch_queue_idle_seconds or 0)
        if self._type_idle_seconds > 0:
            self._type_gc_interval = max(1.0, self._type_idle_seconds / 2)

    def _ensure_type_gc(self) -> None:
        if self._type_gc_task or self._type_idle_seconds <= 0:
            return
        self._type_gc_task = asyncio.create_task(self._type_gc_loop(), name="biz-dispatch-gc")

    async def _enqueue_type(self, message_type: str, envelope: WsEnvelope) -> None:
        queue = self._get_type_queue(message_type)
        self._type_last_activity[message_type] = asyncio.get_running_loop().time()
        if not queue.full() or self._dispatch_queue_overflow == "block":
            await queue.put(envelope)
            return
        if self._dispatch_queue_overflow == "drop_new":
            LOGGER.warning("Dispatch queue full for %s; dropping message id=%s", message_type, envelope.id)
            return
        if self._dispatch_queue_overflow == "drop_oldest":
            try:
                dropped = queue.get_nowait()
            except asyncio.QueueEmpty:
                dropped = None
            else:
                LOGGER.warning(
                    "Dispatch queue full for %s; dropping oldest id=%s",
                    message_type,
                    dropped.id,
                )
            await queue.put(envelope)

    def _get_type_queue(self, message_type: str) -> asyncio.Queue[WsEnvelope]:
        queue = self._type_queues.get(message_type)
        if queue is not None:
            return queue
        queue = asyncio.Queue(maxsize=self._dispatch_queue_max)
        self._type_queues[message_type] = queue
        self._type_last_activity[message_type] = asyncio.get_running_loop().time()
        task = asyncio.create_task(
            self._type_loop(message_type, queue),
            name=f"biz-dispatch-{message_type}",
        )
        self._type_tasks[message_type] = task
        return queue

    async def _type_loop(self, message_type: str, queue: asyncio.Queue[WsEnvelope]) -> None:
        while True:
            try:
                envelope = await queue.get()
                self._type_busy[message_type] = self._type_busy.get(message_type, 0) + 1
                try:
                    await self._dispatch_with_limit(envelope)
                finally:
                    remaining = self._type_busy.get(message_type, 1) - 1
                    if remaining <= 0:
                        self._type_busy.pop(message_type, None)
                    else:
                        self._type_busy[message_type] = remaining
                    self._type_last_activity[message_type] = asyncio.get_running_loop().time()
            except asyncio.CancelledError:
                raise
            except Exception:  # noqa: BLE001
                LOGGER.exception("Dispatch loop failed for %s", message_type)

    async def _dispatch_with_limit(self, envelope: WsEnvelope) -> None:
        if self._dispatch_semaphore:
            await self._dispatch_semaphore.acquire()
            try:
                await self._dispatch(envelope)
            finally:
                self._dispatch_semaphore.release()
        else:
            await self._dispatch(envelope)

    async def _stop_type_tasks(self) -> None:
        if not self._type_tasks:
            return
        tasks = list(self._type_tasks.values())
        self._type_tasks.clear()
        self._type_queues.clear()
        self._type_last_activity.clear()
        self._type_busy.clear()
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _type_gc_loop(self) -> None:
        try:
            while True:
                await asyncio.sleep(self._type_gc_interval)
                now = asyncio.get_running_loop().time()
                for message_type, queue in list(self._type_queues.items()):
                    if queue.qsize() > 0:
                        continue
                    if self._type_busy.get(message_type, 0) > 0:
                        continue
                    last = self._type_last_activity.get(message_type, now)
                    if (now - last) < self._type_idle_seconds:
                        continue
                    task = self._type_tasks.pop(message_type, None)
                    self._type_queues.pop(message_type, None)
                    self._type_last_activity.pop(message_type, None)
                    if task:
                        task.cancel()
                        with contextlib.suppress(asyncio.CancelledError):
                            await task
        except asyncio.CancelledError:
            raise

    async def _stop_type_gc(self) -> None:
        if not self._type_gc_task:
            return
        task = self._type_gc_task
        self._type_gc_task = None
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task

    async def _dispatch(self, envelope: WsEnvelope) -> None:
        handlers = list(self._handlers.get(envelope.type, []))
        if not handlers:
            LOGGER.debug("No handler registered for %s", envelope.type)
            return
        now = asyncio.get_running_loop().time()
        for handler in handlers:
            try:
                key = (envelope.type, handler)
                backoff_until = self._handler_backoff_until.get(key)
                if backoff_until and backoff_until > now:
                    LOGGER.warning(
                        "Handler in cooldown for %s (%.0fms remaining)",
                        envelope.type,
                        (backoff_until - now) * 1000,
                    )
                    continue
                if self._dispatch_timeout > 0:
                    await asyncio.wait_for(handler(envelope), timeout=self._dispatch_timeout)
                else:
                    await handler(envelope)
                self._handler_failures.pop(key, None)
                self._handler_backoff_until.pop(key, None)
            except asyncio.CancelledError:
                raise
            except asyncio.TimeoutError as exc:
                self._record_handler_failure(envelope.type, handler, exc, "timeout")
            except Exception:  # noqa: BLE001
                self._record_handler_failure(envelope.type, handler, None, "error")

    def _record_handler_failure(
        self,
        message_type: str,
        handler: Handler,
        exc: Optional[BaseException],
        reason: str,
    ) -> None:
        key = (message_type, handler)
        count = self._handler_failures.get(key, 0) + 1
        self._handler_failures[key] = count
        if exc:
            LOGGER.warning("Handler failed for %s (%s): %s", message_type, reason, exc)
        else:
            LOGGER.exception("Handler error for %s", message_type)
        if (
            self._dispatch_failure_limit > 0
            and count >= self._dispatch_failure_limit
            and self._dispatch_failure_cooldown > 0
        ):
            backoff_until = asyncio.get_running_loop().time() + self._dispatch_failure_cooldown
            self._handler_backoff_until[key] = backoff_until
            LOGGER.warning(
                "Handler cooldown for %s (%.2fs) after %s failures",
                message_type,
                self._dispatch_failure_cooldown,
                count,
            )

    async def _on_session_disconnect(self, exc: Exception) -> None:
        LOGGER.warning("Session disconnected: %s", exc)
        await self._run_hooks(self._disconnect_hooks, exc)

    def register_handler(self, message_type: str, handler: Handler) -> None:
        """Register a handler for a specific business message type."""
        LOGGER.debug("Registering handler for %s: %s", message_type, handler)
        self._handlers[message_type].append(handler)

    def unregister_handler(self, message_type: str, handler: Handler) -> None:
        handlers = self._handlers.get(message_type, [])
        if handler in handlers:
            handlers.remove(handler)

    def add_disconnect_hook(self, hook: Callable[[Exception], Awaitable[None] | None]) -> None:
        """Register a hook invoked when the session disconnects."""
        self._disconnect_hooks.append(hook)

    def add_stop_hook(self, hook: Callable[[], Awaitable[None] | None]) -> None:
        """Register a hook invoked during client stop."""
        self._stop_hooks.append(hook)

    async def send_biz(
        self,
        message_type: str,
        payload: Any,
        *,
        require_ack: bool = False,
        corr: Optional[str] = None,
        seq: Optional[int] = None,
        session_seq: Optional[int] = None,
    ) -> None:
        """Send a biz.* frame via the session."""
        self._ensure_layers()
        assert self.session is not None
        envelope = self.session.build_envelope(
            message_type,
            payload,
            request_ack=require_ack,
            corr=corr,
            seq=seq,
            session_seq=session_seq,
        )
        await self.session.send(envelope)

    def next_message_id(self, prefix: str) -> str:
        self._ensure_layers()
        assert self.session is not None
        return self.session.next_message_id(prefix)

    async def _run_hooks(self, hooks: List[Callable], *args: Any) -> None:
        for hook in list(hooks):
            try:
                result = hook(*args)
                if inspect.isawaitable(result):
                    await result
            except Exception:  # noqa: BLE001
                LOGGER.exception("Lifecycle hook failed: %s", hook)
