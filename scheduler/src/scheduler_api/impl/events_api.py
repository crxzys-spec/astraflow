from __future__ import annotations

from typing import Optional

from scheduler_api.http.errors import bad_request
from fastapi.responses import StreamingResponse

from scheduler_api.apis.events_api_base import BaseEventsApi
from scheduler_api.auth.roles import RUN_VIEW_ROLES, require_roles

from scheduler_api.infra.sse import (
    SseConnection,
    SubscriptionFilter,
    connection_registry,
    event_store,
)


class EventsApiImpl(BaseEventsApi):
    def __init__(self, tenant: str = "default") -> None:
        self.tenant = tenant

    async def sse_global_events(
        self,
        client_session_id: str,
        last_event_id: Optional[str],
    ) -> StreamingResponse:
        require_roles(*RUN_VIEW_ROLES)
        if not client_session_id:
            raise bad_request("clientSessionId is required")

        subscription = SubscriptionFilter()
        connection = SseConnection(
            tenant=self.tenant,
            client_session_id=client_session_id,
            filters=subscription,
        )

        replay_events = event_store.replay(self.tenant, last_event_id)
        await connection_registry.add(connection)

        async def event_stream():
            try:
                async for payload in connection.iter_stream(replay_events):
                    yield payload
            finally:
                await connection_registry.remove(connection)
                await connection.close()

        return StreamingResponse(event_stream(), media_type="text/event-stream")
