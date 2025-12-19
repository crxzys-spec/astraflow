"""Control-plane orchestration for the worker.

This module wires the pure session layer (transport + control.* + ACK) with the
business layer (biz.*). The business layer must not leak into the session layer.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, Optional

from worker.agent.concurrency import ConcurrencyGuard
from worker.agent.packages import AdapterRegistry, PackageManager
from worker.agent.resource_registry import ResourceRegistry
from worker.agent.runner import Runner
from worker.config import WorkerSettings
from worker.control_plane.biz_layer import BizLayer
from worker.control_plane.session_client import ControlPlaneSession
from worker.transport import ControlPlaneTransport

LOGGER = logging.getLogger(__name__)


@dataclass
class ControlPlaneClient:
    """Wires the session + biz layers and routes inbound application frames."""

    settings: WorkerSettings
    transport_factory: Callable[[WorkerSettings], ControlPlaneTransport]
    command_handler: Optional[Callable[[dict[str, Any]], Awaitable[None]]] = None
    package_handler: Optional[Callable[[str, dict[str, Any]], Awaitable[None]]] = None
    adapter_registry: Optional[AdapterRegistry] = None
    runner: Optional[Runner] = None
    package_manager: Optional[PackageManager] = None
    resource_registry: Optional[ResourceRegistry] = None
    package_inventory: list[dict[str, Any]] = field(default_factory=list)
    package_manifests: list[dict[str, Any]] = field(default_factory=list)
    concurrency_guard: ConcurrencyGuard = field(default_factory=ConcurrencyGuard)

    session: Optional[ControlPlaneSession] = field(default=None, init=False, repr=False)
    biz: Optional[BizLayer] = field(default=None, init=False, repr=False)
    _route_task: Optional[asyncio.Task[None]] = field(default=None, init=False, repr=False)

    def _ensure_layers(self) -> None:
        if self.session is None:
            self.session = ControlPlaneSession(
                settings=self.settings,
                transport_factory=self.transport_factory,
                concurrency_guard=self.concurrency_guard,
                resource_registry=self.resource_registry,
                on_disconnect=self._on_session_disconnect,
            )
        else:
            self.session.resource_registry = self.resource_registry

        if self.biz is None:
            assert self.session is not None
            self.biz = BizLayer(
                settings=self.settings,
                build_envelope=self.session.build_envelope,
                send=self.session.send,
                next_message_id=self.session.next_message_id,
                concurrency_guard=self.concurrency_guard,
                runner=self.runner,
                command_handler=self.command_handler,
                package_handler=self.package_handler,
                resource_registry=self.resource_registry,
            )
        else:
            self.biz.runner = self.runner
            self.biz.command_handler = self.command_handler
            self.biz.package_handler = self.package_handler
            self.biz.resource_registry = self.resource_registry

    async def start(self) -> None:
        self._ensure_layers()
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

        self._ensure_layers()
        if self.biz is not None:
            await self.biz.cancel_dispatch_tasks()
            self.biz.cancel_pending_next()
        if self.session is not None:
            await self.session.stop()

    async def _route_loop(self) -> None:
        assert self.session is not None
        assert self.biz is not None
        try:
            async for envelope in self.session.messages():
                await self.biz.handle_envelope(envelope)
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001
            LOGGER.exception("Business routing loop crashed")
            self.biz.cancel_pending_next()

    async def _on_session_disconnect(self, exc: Exception) -> None:
        if self.biz is None:
            return
        LOGGER.warning("Session disconnected; cancelling pending middleware.next waits: %s", exc)
        self.biz.cancel_pending_next()
