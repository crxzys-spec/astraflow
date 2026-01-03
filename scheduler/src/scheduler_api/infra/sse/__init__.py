from __future__ import annotations

from .connection import SseConnection, SubscriptionFilter
from .models import UiEventEnvelope, UiEventScope, UiEventType
from .publisher import EventPublisher
from .registry import ConnectionRegistry
from .store import EventStore


__all__ = [
    "SseConnection",
    "SubscriptionFilter",
    "UiEventEnvelope",
    "UiEventScope",
    "UiEventType",
    "event_store",
    "connection_registry",
    "event_publisher",
]


event_store = EventStore(max_events_per_tenant=1000)
connection_registry = ConnectionRegistry()
event_publisher = EventPublisher(connection_registry, event_store)
