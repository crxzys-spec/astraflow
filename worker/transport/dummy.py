"""No-op transport for offline testing."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from .base import ControlPlaneTransport

LOGGER = logging.getLogger(__name__)


class DummyTransport(ControlPlaneTransport):
    """Temporary transport placeholder until WebSocket integration lands."""

    def __init__(self, settings=None) -> None:
        self._settings = settings

    async def connect(self) -> None:
        LOGGER.debug("Dummy transport connect()")

    async def send(self, message: dict[str, Any]) -> None:
        LOGGER.debug("Dummy transport send(): %s", message)

    async def receive(self) -> dict[str, Any]:
        LOGGER.debug("Dummy transport receive() (no-op)")
        await asyncio.sleep(3600)
        return {}

    async def close(self) -> None:
        LOGGER.debug("Dummy transport close()")
