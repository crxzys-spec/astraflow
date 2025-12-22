"""Worker bootstrap entrypoint for network/session wiring."""

from __future__ import annotations

import asyncio
import logging
from typing import Type

from worker.agent.packages import AdapterRegistry, PackageManager
from worker.agent.resource_registry import ResourceRegistry
from worker.agent.runner import Runner
from worker.config import get_settings
from worker.biz_handlers.next_handler import NextHandler
from worker.biz_handlers.dispatch_handler import DispatchHandler
from worker.network.client import NetworkClient
from worker.network.transport.base import BaseTransport
from worker.network.transport.dummy import DummyTransport
from worker.network.transport.websocket import WebSocketTransport
from shared.models.biz.pkg.install import PackageInstallCommand
from shared.models.biz.pkg.uninstall import PackageUninstallCommand

LOGGER = logging.getLogger(__name__)
_connection: NetworkClient | None = None


def _require_psutil() -> None:
    try:
        import psutil  # type: ignore
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError("psutil is required for worker metrics; install psutil") from exc


async def setup() -> None:
    """Construct, wire, and start the network client (no return)."""

    global _connection
    _require_psutil()
    settings = get_settings()
    registry: AdapterRegistry = AdapterRegistry()
    package_manager: PackageManager = PackageManager(settings, registry)
    resource_registry = ResourceRegistry(worker_name=settings.worker_name, base_dir=settings.data_dir)
    package_inventory, package_manifests = package_manager.collect_inventory()
    resolved_cls: Type[BaseTransport]
    resolved_cls = WebSocketTransport if settings.transport == "websocket" else DummyTransport
    LOGGER.debug("Initialising worker connection via %s", resolved_cls.__name__)
    runner = Runner(registry, default_exec_mode=settings.handler_exec_mode_default)

    connection = NetworkClient(
        settings=settings,
        transport_factory=lambda s: resolved_cls(s),
        package_handler=None,
        adapter_registry=registry,
        runner=runner,
        package_manager=package_manager,
        resource_registry=resource_registry,
        package_inventory=package_inventory,
        package_manifests=package_manifests,
    )

    connection._ensure_layers()
    next_handler = NextHandler(
        send_biz=connection.send_biz,
        next_message_id=connection.next_message_id,
    )
    dispatch_handler = DispatchHandler(
        settings=settings,
        send_biz=connection.send_biz,
        next_handler=next_handler,
        concurrency_guard=connection.concurrency_guard,
        runner=runner,
        resource_registry=resource_registry,
    )
    connection.register_handler("biz.exec.dispatch", dispatch_handler.handle)
    connection.register_handler("biz.exec.next.response", next_handler.handle_next_response)

    async def _cleanup() -> None:
        await dispatch_handler.cancel_dispatch_tasks()
        next_handler.cancel_pending_next()

    connection.add_disconnect_hook(lambda exc=None: next_handler.cancel_pending_next())
    connection.add_stop_hook(_cleanup)

    async def _pkg_install(envelope):
        command = PackageInstallCommand.model_validate(envelope.payload)
        if not connection.package_manager:
            LOGGER.warning("Package install requested but package manager is unavailable")
            return
        if not command.url:
            LOGGER.warning("Package install missing url name=%s version=%s", command.name, command.version)
            return
        try:
            await asyncio.to_thread(
                connection.package_manager.install,
                command.name,
                command.version,
                str(command.url),
                command.sha256,
            )
        except Exception:  # noqa: BLE001
            LOGGER.exception("Package install failed name=%s version=%s", command.name, command.version)
            return
        await connection.refresh_registration()

    async def _pkg_uninstall(envelope):
        command = PackageUninstallCommand.model_validate(envelope.payload)
        if not connection.package_manager:
            LOGGER.warning("Package uninstall requested but package manager is unavailable")
            return
        versions: list[str] = []
        if command.version:
            versions = [command.version]
        else:
            inventory, _ = connection.package_manager.collect_inventory()
            versions = [item["version"] for item in inventory if item.get("name") == command.name]
        if not versions:
            LOGGER.warning("Package uninstall requested but no versions found name=%s", command.name)
            return
        for version in versions:
            try:
                await asyncio.to_thread(connection.package_manager.uninstall, command.name, version)
            except Exception:  # noqa: BLE001
                LOGGER.exception("Package uninstall failed name=%s version=%s", command.name, version)
        await connection.refresh_registration()

    connection.register_handler("biz.pkg.install", _pkg_install)
    connection.register_handler("biz.pkg.uninstall", _pkg_uninstall)

    await connection.start()
    _connection = connection


async def serve_forever() -> None:
    """Start the worker network stack and keep the process alive."""

    await setup()
    try:
        await asyncio.Future()  # block until cancelled
    except asyncio.CancelledError:
        LOGGER.info("Worker shutdown requested")
        raise
    finally:
        if _connection:
            await _connection.stop()
