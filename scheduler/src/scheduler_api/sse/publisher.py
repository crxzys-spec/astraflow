from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable

from .connection import SseConnection
from .models import UiEventEnvelope
from .registry import ConnectionRegistry
from .store import EventStore


class EventPublisher:
    """Dispatch UiEventEnvelope instances to interested SSE connections."""

    def __init__(self, registry: ConnectionRegistry, store: EventStore) -> None:
        self._registry = registry
        self._store = store

    async def publish(self, envelope: UiEventEnvelope) -> None:
        scope = envelope.scope
        event_id = self._store.next_id(scope.tenant)
        occurred_at = envelope.occurredAt or datetime.now(timezone.utc)
        final_envelope = envelope.model_copy(update={"id": event_id, "occurredAt": occurred_at})
        self._store.append(scope.tenant, final_envelope)
        connections = await self._registry.match(scope)
        for connection in connections:
            await connection.enqueue(final_envelope)
