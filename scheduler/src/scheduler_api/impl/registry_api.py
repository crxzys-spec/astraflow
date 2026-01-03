from __future__ import annotations

from scheduler_api.apis.registry_api_base import BaseRegistryApi
from scheduler_api.auth.roles import WORKFLOW_EDIT_ROLES, WORKFLOW_VIEW_ROLES, require_roles
from scheduler_api.http.errors import bad_request, not_found
from scheduler_api.models.registry_account_link import RegistryAccountLink
from scheduler_api.models.registry_account_link_request import RegistryAccountLinkRequest
from scheduler_api.models.registry_workflow_import_request import RegistryWorkflowImportRequest
from scheduler_api.models.registry_workflow_import_response import RegistryWorkflowImportResponse
from scheduler_api.service.registry_accounts import registry_account_service
from scheduler_api.service.registry_imports import (
    RegistryImportError,
    RegistryImportNotFoundError,
    registry_import_service,
)


class RegistryApiImpl(BaseRegistryApi):
    async def get_registry_account(self) -> RegistryAccountLink:
        token = require_roles(*WORKFLOW_VIEW_ROLES)
        link = registry_account_service.get_by_user_id(token.sub)
        if link is None:
            raise not_found("Registry account not linked.", error="registry_account_not_found")
        return RegistryAccountLink.from_dict(link.to_dict())

    async def link_registry_account(
        self,
        registry_account_link_request: RegistryAccountLinkRequest,
    ) -> RegistryAccountLink:
        token = require_roles(*WORKFLOW_EDIT_ROLES)
        if registry_account_link_request is None:
            raise bad_request("Registry account payload is required.")
        snapshot = registry_account_service.upsert(
            user_id=token.sub,
            registry_user_id=registry_account_link_request.registry_user_id,
            registry_username=registry_account_link_request.registry_username,
        )
        return RegistryAccountLink.from_dict(snapshot.to_dict())

    async def unlink_registry_account(self) -> None:
        token = require_roles(*WORKFLOW_EDIT_ROLES)
        link = registry_account_service.get_by_user_id(token.sub)
        if link is None:
            raise not_found("Registry account not linked.", error="registry_account_not_found")
        registry_account_service.delete(token.sub)
        return None

    async def import_registry_workflow(
        self,
        registry_workflow_import_request: RegistryWorkflowImportRequest,
    ) -> RegistryWorkflowImportResponse:
        token = require_roles(*WORKFLOW_EDIT_ROLES)
        if registry_workflow_import_request is None:
            raise bad_request("Import payload is required.")
        try:
            result = registry_import_service.import_workflow(
                package_id=registry_workflow_import_request.package_id,
                version_id=registry_workflow_import_request.version_id,
                version=registry_workflow_import_request.version,
                actor_id=token.sub,
                name_override=registry_workflow_import_request.name,
            )
        except RegistryImportNotFoundError as exc:
            raise not_found(exc.message, error="registry_not_found") from exc
        except RegistryImportError as exc:
            raise bad_request(exc.message, error="registry_import_failed", details=exc.details) from exc
        return RegistryWorkflowImportResponse.from_dict(result.to_dict())
