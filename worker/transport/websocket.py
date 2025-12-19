"""WebSocket transport implementation."""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

from fastapi.encoders import jsonable_encoder
import websockets
from websockets.client import WebSocketClientProtocol

from worker.config import WorkerSettings
from worker.transport.base import ControlPlaneTransport

LOGGER = logging.getLogger(__name__)


class WebSocketTransport(ControlPlaneTransport):
    """WebSocket-based control-plane transport."""

    def __init__(self, settings: WorkerSettings) -> None:
        self._settings = settings
        self._ws: Optional[WebSocketClientProtocol] = None

    async def connect(self) -> None:
        LOGGER.info("Connecting to scheduler WebSocket at %s", self._settings.scheduler_ws_url)
        self._ws = await websockets.connect(str(self._settings.scheduler_ws_url))

    async def send(self, message: dict[str, Any]) -> None:
        if not self._ws:
            raise RuntimeError("WebSocket transport not connected")
        payload = json.dumps(jsonable_encoder(message))
        LOGGER.debug("WebSocket send: %s", payload)
        await self._ws.send(payload)

    async def receive(self) -> dict[str, Any]:
        if not self._ws:
            raise RuntimeError("WebSocket transport not connected")
        raw = await self._ws.recv()
        LOGGER.debug("WebSocket receive: %s", raw)
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        return json.loads(raw)

    async def close(self) -> None:
        if self._ws:
            LOGGER.info("Closing WebSocket transport")
            await self._ws.close()
            self._ws = None
