"""WebSocket transport wrapper for control-plane I/O."""

from __future__ import annotations

import json
from typing import Any

from fastapi import WebSocket
from fastapi.encoders import jsonable_encoder

from shared.models.session import WsEnvelope

from .base import BaseTransport


class WebSocketTransport(BaseTransport):
    """Thin wrapper around FastAPI WebSocket."""

    def __init__(self, websocket: WebSocket) -> None:
        self._websocket = websocket

    @property
    def websocket(self) -> WebSocket:
        return self._websocket

    @property
    def client(self) -> Any:
        return self._websocket.client

    async def accept(self) -> None:
        await self._websocket.accept()

    async def receive_envelope(self) -> WsEnvelope:
        message = await self._websocket.receive_json()
        return WsEnvelope.model_validate(message)

    async def send(self, payload: WsEnvelope | dict[str, Any]) -> None:
        if isinstance(payload, WsEnvelope):
            data = payload.model_dump(by_alias=True, exclude_none=True)
        else:
            data = jsonable_encoder(payload)
        await self._websocket.send_text(json.dumps(jsonable_encoder(data)))

    async def close(self, *, code: int = 1011, reason: str = "internal error") -> None:
        await self._websocket.close(code=code, reason=reason)
