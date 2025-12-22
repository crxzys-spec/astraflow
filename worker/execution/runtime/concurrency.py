"""Lightweight concurrency guard to enforce single-flight execution."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncIterator, Set


class ConcurrencyGuard:
    """Tracks in-flight keys and prevents duplicate execution."""

    def __init__(self) -> None:
        self._inflight: Set[str] = set()
        self._lock = asyncio.Lock()

    @asynccontextmanager
    async def acquire(self, key: str) -> AsyncIterator[bool]:
        if not key:
            yield True
            return
        async with self._lock:
            if key in self._inflight:
                yield False
                return
            self._inflight.add(key)
        try:
            yield True
        finally:
            async with self._lock:
                self._inflight.discard(key)

    def inflight(self) -> int:
        """Return the current number of in-flight concurrency keys."""

        return len(self._inflight)
