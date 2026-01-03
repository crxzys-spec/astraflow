from __future__ import annotations

from collections import defaultdict, deque
from typing import Deque, Dict, Iterable, List, Optional

from .models import UiEventEnvelope


class EventStore:
    """Simple per-tenant in-memory event buffer for replay support."""

    def __init__(self, *, max_events_per_tenant: int = 1000) -> None:
        self._max_events = max_events_per_tenant
        self._events: Dict[str, Deque[UiEventEnvelope]] = defaultdict(deque)
        self._counters: Dict[str, int] = defaultdict(int)

    def next_id(self, tenant: str) -> str:
        self._counters[tenant] += 1
        return str(self._counters[tenant])

    def append(self, tenant: str, envelope: UiEventEnvelope) -> None:
        buffer = self._events[tenant]
        buffer.append(envelope.model_copy(deep=True))
        while len(buffer) > self._max_events:
            buffer.popleft()
        try:
            current_id = int(envelope.id)
        except (ValueError, TypeError):
            return
        self._counters[tenant] = max(self._counters[tenant], current_id)

    def replay(self, tenant: str, last_event_id: Optional[str]) -> Iterable[UiEventEnvelope]:
        buffer = self._events.get(tenant)
        if not buffer:
            return []

        events: List[UiEventEnvelope] = list(buffer)
        if not last_event_id:
            return [event.model_copy(update={"replayed": True}) for event in events]

        for index, event in enumerate(events):
            if event.id == last_event_id:
                remaining = events[index + 1 :]
                return [event.model_copy(update={"replayed": True}) for event in remaining]

        # last_event_id not found; replay entire buffer to resynchronise
        return [event.model_copy(update={"replayed": True}) for event in events]
