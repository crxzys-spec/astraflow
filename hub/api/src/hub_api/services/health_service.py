from __future__ import annotations

from datetime import datetime, timezone

from hub_api.models.health_status import HealthStatus


class HealthService:
    async def get_health(self) -> HealthStatus:
        return HealthStatus(
            status="ok",
            version="0.1.0",
            timestamp=datetime.now(timezone.utc),
        )
