"""Control-plane network server facade for worker connections."""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from typing import Awaitable, Callable, Optional

from fastapi import WebSocket, WebSocketDisconnect

from shared.models.session import WsEnvelope

from scheduler_api.config.settings import get_settings
from .manager import WorkerSession, worker_manager
from .session import ControlPlaneSession
from .session_tokens import issue_session_token, validate_session_token
from .transport import WebSocketTransport

LOGGER = logging.getLogger(__name__)

Handler = Callable[[WsEnvelope, Optional[WorkerSession]], Awaitable[None]]
ConnectionTaskFactory = Callable[[Callable[[], Optional[WorkerSession]]], Awaitable[None]]


class ControlPlaneServer:
    """Handles websocket sessions and routes envelopes to registered handlers."""

    def __init__(
        self,
        *,
        manager=worker_manager,
        settings=None,
        scheduler_id: Optional[str] = None,
        token_issuer: Callable[..., tuple[str, float]] = issue_session_token,
        token_validator: Callable[..., bool] = validate_session_token,
    ) -> None:
        self._manager = manager
        self._settings = settings or get_settings()
        self._scheduler_id = scheduler_id or self._manager.scheduler_id
        self._token_issuer = token_issuer
        self._token_validator = token_validator
        self._handlers: dict[str, list[Handler]] = defaultdict(list)
        self._connection_tasks: list[ConnectionTaskFactory] = []

    def register_handler(self, message_type: str, handler: Handler) -> None:
        self._handlers[message_type].append(handler)

    def add_connection_task(self, task_factory: ConnectionTaskFactory) -> None:
        self._connection_tasks.append(task_factory)

    @property
    def scheduler_id(self) -> str:
        return self._scheduler_id

    async def send_envelope(self, worker: WorkerSession | str, payload: dict | WsEnvelope) -> None:
        await self._manager.send_envelope(worker, payload)

    async def handle_websocket(self, websocket: WebSocket) -> None:
        transport = WebSocketTransport(websocket)
        await transport.accept()
        session_handler = ControlPlaneSession(
            transport=transport,
            manager=self._manager,
            settings=self._settings,
            scheduler_id=self._scheduler_id,
            token_issuer=self._token_issuer,
            token_validator=self._token_validator,
        )
        LOGGER.info("Worker connection opened from %s", transport.client)

        def _session_provider() -> Optional[WorkerSession]:
            return session_handler.session

        tasks: list[asyncio.Task] = []
        for factory in self._connection_tasks:
            task = asyncio.create_task(factory(_session_provider))
            tasks.append(task)

        try:
            while True:
                envelope = await transport.receive_envelope()
                ready = await session_handler.handle_envelope(envelope)
                if session_handler.closing:
                    break
                for ready_envelope in ready:
                    await self._dispatch_handlers(ready_envelope, session_handler.session)

        except WebSocketDisconnect:
            LOGGER.info("Worker connection closed")
        except Exception:
            LOGGER.exception("Worker control-plane encountered an error; closing connection")
            await transport.close(code=1011, reason="internal error")
        finally:
            for task in tasks:
                task.cancel()
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
            session = session_handler.session
            if session:
                self._manager.mark_disconnected(session.worker_instance_id, session.worker_name)
                LOGGER.info("Worker %s marked disconnected", session.worker_name)

    async def _dispatch_handlers(self, envelope: WsEnvelope, session: Optional[WorkerSession]) -> None:
        handlers = list(self._handlers.get(envelope.type, []))
        if not handlers:
            LOGGER.warning("Unhandled message type %s", envelope.type)
            return
        for handler in handlers:
            try:
                await handler(envelope, session)
            except Exception:  # noqa: BLE001
                LOGGER.exception("Handler failed for %s", envelope.type)
