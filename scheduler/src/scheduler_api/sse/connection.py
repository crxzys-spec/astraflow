from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import AsyncIterator, Iterable, Optional, Set
from uuid import uuid4

from .models import UiEventEnvelope, UiEventScope, serialize_envelope


@dataclass(slots=True)
class SubscriptionFilter:
    run_ids: Optional[Set[str]] = None

    def matches(self, scope: UiEventScope) -> bool:
        if not self.run_ids:
            return True
        if scope.runId is None:
            return False
        return scope.runId in self.run_ids


class SseConnection:
    """Represents an active SSE connection."""

    _SENTINEL = object()
    _HEARTBEAT_COMMENT = b": heartbeat\n\n"

    def __init__(
        self,
        *,
        tenant: str,
        client_session_id: str,
        filters: Optional[SubscriptionFilter] = None,
        heartbeat_interval: float = 45.0,
    ) -> None:
        self.tenant = tenant
        self.client_session_id = client_session_id
        self.filters = filters or SubscriptionFilter()
        self._queue: asyncio.Queue[object] = asyncio.Queue()
        self._closed = False
        self._id = uuid4().hex
        self._heartbeat_interval = heartbeat_interval

    def __hash__(self) -> int:  # pragma: no cover - used for registry bookkeeping
        return hash(self._id)

    def __eq__(self, other: object) -> bool:  # pragma: no cover
        if not isinstance(other, SseConnection):
            return False
        return self._id == other._id

    async def enqueue(self, envelope: UiEventEnvelope) -> None:
        if self._closed:
            return
        await self._queue.put(envelope)

    async def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            self._queue.put_nowait(self._SENTINEL)
        except asyncio.QueueFull:  # pragma: no cover - queue unbounded
            await self._queue.put(self._SENTINEL)

    async def iter_stream(
        self,
        replay_events: Iterable[UiEventEnvelope],
    ) -> AsyncIterator[bytes]:
        try:
            for event in replay_events:
                # Mark replayed deliveries explicitly
                if event.replayed is not True:
                    event = event.model_copy(update={"replayed": True})
                yield serialize_envelope(event)

            while True:
                try:
                    item = await asyncio.wait_for(
                        self._queue.get(), timeout=self._heartbeat_interval
                    )
                except asyncio.TimeoutError:
                    if self._closed:
                        break
                    yield self._HEARTBEAT_COMMENT
                    continue
                if item is self._SENTINEL:
                    break
                envelope = item  # type: ignore[assignment]
                yield serialize_envelope(envelope)
        finally:
            self._closed = True
