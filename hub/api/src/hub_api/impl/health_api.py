from __future__ import annotations

from hub_api.apis.health_api_base import BaseHealthApi
from hub_api.models.health_status import HealthStatus
from hub_api.services.health_service import HealthService

_service = HealthService()


class HealthApiImpl(BaseHealthApi):
    async def get_health(self) -> HealthStatus:
        return await _service.get_health()
