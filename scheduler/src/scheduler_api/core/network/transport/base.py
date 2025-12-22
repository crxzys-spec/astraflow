"""Transport abstractions for control-plane server connections."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from shared.models.session import WsEnvelope


class BaseTransport(ABC):
    """Abstract WebSocket-like transport for scheduler control-plane IO."""

    @property
    @abstractmethod
    def client(self) -> Any:
        ...

    @abstractmethod
    async def accept(self) -> None:
        ...

    @abstractmethod
    async def receive_envelope(self) -> WsEnvelope:
        ...

    @abstractmethod
    async def send(self, payload: WsEnvelope | dict[str, Any]) -> None:
        ...

    @abstractmethod
    async def close(self, *, code: int = 1011, reason: str = "internal error") -> None:
        ...
