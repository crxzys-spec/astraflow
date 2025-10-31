"""Worker bootstrap helpers."""

from __future__ import annotations

import asyncio
import logging
from typing import Optional, Type

from .config import WorkerSettings, get_settings
from .connection import ControlPlaneConnection, ControlPlaneTransport, DummyTransport
from .transport import WebSocketTransport
from .packages import AdapterRegistry, PackageManager
from .runner import Runner
from .resource_registry import ResourceRegistry
from shared.models.ws.pkg.event import PackageEvent
from shared.models.ws.envelope import WsEnvelope

LOGGER = logging.getLogger(__name__)


def build_connection(
    *,
    settings: WorkerSettings | None = None,
    transport_cls: Type[ControlPlaneTransport] | None = None,
    command_handler=None,
    package_handler=None,
    registry: Optional[AdapterRegistry] = None,
    package_manager: Optional[PackageManager] = None,
) -> ControlPlaneConnection:
    """Construct a control-plane connection instance."""

    settings = settings or get_settings()
    registry = registry or AdapterRegistry()
    package_manager = package_manager or PackageManager(settings, registry)
    resource_registry = ResourceRegistry(worker_id=settings.worker_id, base_dir=settings.data_dir)
    resolved_cls: Type[ControlPlaneTransport]
    if transport_cls is not None:
        resolved_cls = transport_cls
    else:
        resolved_cls = WebSocketTransport if settings.transport == "websocket" else DummyTransport
    LOGGER.debug("Initialising worker connection via %s", resolved_cls.__name__)
    runner = Runner(registry)
    connection = ControlPlaneConnection(
        settings=settings,
        transport_factory=lambda s: resolved_cls(s),
        command_handler=command_handler,
        package_handler=package_handler,
        adapter_registry=registry,
        runner=runner,
        package_manager=package_manager,
        resource_registry=resource_registry,
    )

    if package_handler is None:

        async def default_package_handler(action: str, message: dict) -> None:
            envelope = WsEnvelope.model_validate(message)
            payload = envelope.payload or {}
            name = payload.get("package") or payload.get("name")
            version = payload.get("version")
            if not name or not version:
                LOGGER.error("Package command missing name/version: %s", message)
                return
            try:
                if action == "install":
                    url = payload.get("url")
                    checksum = payload.get("sha256")
                    if not url:
                        raise ValueError("Package install command missing url")
                    descriptor = await asyncio.to_thread(
                        package_manager.install,
                        name,
                        version,
                        url,
                        checksum,
                    )
                    await connection.send_package_event(
                        PackageEvent(
                            name=descriptor.name,
                            version=descriptor.version,
                            status=PackageEvent.Status.installed,
                        )
                    )
                elif action == "uninstall":
                    await asyncio.to_thread(package_manager.uninstall, name, version)
                    await connection.send_package_event(
                        PackageEvent(
                            name=name,
                            version=version,
                            status=PackageEvent.Status.installed,
                            details={"message": "uninstall-complete", "operation": "uninstall"},
                        )
                    )
                else:
                    LOGGER.warning("Unsupported package action %s", action)
            except Exception as exc:  # noqa: BLE001
                LOGGER.exception("Package command failed: %s", exc)
                await connection.send_package_event(
                    PackageEvent(
                        name=name or "unknown",
                        version=version or "unknown",
                        status=PackageEvent.Status.failed,
                        details={"error": str(exc)},
                    )
                )

        connection.package_handler = default_package_handler

    return connection


async def start_control_plane(connection: ControlPlaneConnection | None = None) -> ControlPlaneConnection:
    """Establish a control-plane session (handshake -> register -> heartbeat).

    Returns the connection instance so the caller can coordinate shutdown.
    """

    connection = connection or build_connection()
    await connection.start()
    return connection


async def run_forever() -> None:
    """Convenience entry point that boots the control-plane and keeps the loop alive."""

    connection = await start_control_plane()
    try:
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        LOGGER.info("Worker shutdown requested")
        raise
    finally:
        await connection.stop()

