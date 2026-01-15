from __future__ import annotations

from scheduler_api.apis.hub_account_api_base import BaseHubAccountApi
from scheduler_api.auth.roles import WORKFLOW_VIEW_ROLES, require_roles
from scheduler_api.http.errors import bad_request, forbidden
from scheduler_api.models.hub_account import HubAccount
from scheduler_api.service.hub_client import (
    HubClient,
    HubClientError,
    HubNotConfiguredError,
    HubUnauthorizedError,
)


class HubAccountApiImpl(BaseHubAccountApi):
    async def get_hub_account(self) -> HubAccount:
        require_roles(*WORKFLOW_VIEW_ROLES)
        try:
            payload = HubClient.from_settings().get_account()
        except HubNotConfiguredError as exc:
            raise bad_request(str(exc), error="hub_not_configured") from exc
        except HubUnauthorizedError as exc:
            raise forbidden(str(exc), error="hub_unauthorized") from exc
        except HubClientError as exc:
            raise bad_request(str(exc), error="hub_request_failed") from exc
        return HubAccount.from_dict(payload)
