from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Dict, List, Set

from .connection import SseConnection, SubscriptionFilter
from .models import UiEventScope


class ConnectionRegistry:
    """In-memory registry of SSE connections, organised by tenant/session."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._connections: Dict[str, Dict[str, Set[SseConnection]]] = defaultdict(lambda: defaultdict(set))

    async def add(self, connection: SseConnection) -> None:
        async with self._lock:
            tenant_connections = self._connections[connection.tenant]
            tenant_connections[connection.client_session_id].add(connection)

    async def remove(self, connection: SseConnection) -> None:
        async with self._lock:
            tenant_connections = self._connections.get(connection.tenant)
            if not tenant_connections:
                return
            session_connections = tenant_connections.get(connection.client_session_id)
            if not session_connections:
                return
            session_connections.discard(connection)
            if not session_connections:
                tenant_connections.pop(connection.client_session_id, None)
            if not tenant_connections:
                self._connections.pop(connection.tenant, None)

    async def match(self, scope: UiEventScope) -> List[SseConnection]:
        """Return all connections that should receive an event with the given scope."""
        async with self._lock:
            tenant_connections = self._connections.get(scope.tenant)
            if not tenant_connections:
                return []

            candidates: List[SseConnection] = []
            if scope.clientSessionId:
                session_connections = tenant_connections.get(scope.clientSessionId)
                if session_connections:
                    candidates.extend(list(session_connections))
            else:
                for session_connections in tenant_connections.values():
                    candidates.extend(list(session_connections))

        # Filter outside the lock to avoid blocking other operations
        matched = []
        for connection in candidates:
            if connection.filters.matches(scope):
                matched.append(connection)
        return matched
