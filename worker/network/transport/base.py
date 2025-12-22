"""Transport abstractions for scheduler control-plane."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseTransport(ABC):
    """Abstract WebSocket-like transport used by the control-plane connection."""

    @abstractmethod
    async def connect(self) -> None:
        ...

    @abstractmethod
    async def send(self, message: dict[str, Any]) -> None:
        ...

    @abstractmethod
    async def receive(self) -> dict[str, Any]:
        ...

    @abstractmethod
    async def close(self) -> None:
        ...
