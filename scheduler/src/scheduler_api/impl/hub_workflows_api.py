from __future__ import annotations

from scheduler_api.apis.hub_workflows_api_base import BaseHubWorkflowsApi
from scheduler_api.auth.roles import WORKFLOW_EDIT_ROLES, WORKFLOW_VIEW_ROLES, require_roles
from scheduler_api.config.settings import get_api_settings
from scheduler_api.http.errors import bad_request, forbidden, not_found
from scheduler_api.models.hub_workflow_detail import HubWorkflowDetail
from scheduler_api.models.hub_workflow_import_request import HubWorkflowImportRequest
from scheduler_api.models.hub_workflow_import_response import HubWorkflowImportResponse
from scheduler_api.models.hub_workflow_list_response import HubWorkflowListResponse
from scheduler_api.models.hub_workflow_publish_request import HubWorkflowPublishRequest
from scheduler_api.models.hub_workflow_publish_response import HubWorkflowPublishResponse
from scheduler_api.models.hub_workflow_version_detail import HubWorkflowVersionDetail
from scheduler_api.models.hub_workflow_version_list import HubWorkflowVersionList
from scheduler_api.service.hub_client import (
    HubClient,
    HubClientError,
    HubNotConfiguredError,
    HubNotFoundError,
    HubUnauthorizedError,
)
from scheduler_api.service.hub_imports import (
    HubImportError,
    HubImportNotFoundError,
    hub_import_service,
)
from scheduler_api.service.workflow_dependencies import WorkflowPackageDependency, extract_package_dependencies


class HubWorkflowsApiImpl(BaseHubWorkflowsApi):
    async def list_hub_workflows(
        self,
        q: str | None,
        tag: str | None,
        owner: str | None,
        page: int | None,
        page_size: int | None,
    ) -> HubWorkflowListResponse:
        require_roles(*WORKFLOW_VIEW_ROLES)
        try:
            payload = HubClient.from_settings().list_workflows(
                query=q,
                tag=tag,
                owner=owner,
                page=page,
                page_size=page_size,
            )
        except HubNotConfiguredError as exc:
            raise bad_request(str(exc), error="hub_not_configured") from exc
        except HubUnauthorizedError as exc:
            raise forbidden(str(exc), error="hub_unauthorized") from exc
        except HubClientError as exc:
            raise bad_request(str(exc), error="hub_request_failed") from exc
        return HubWorkflowListResponse.from_dict(payload)

    async def publish_hub_workflow(
        self,
        hub_workflow_publish_request: HubWorkflowPublishRequest,
    ) -> HubWorkflowPublishResponse:
        require_roles(*WORKFLOW_EDIT_ROLES)
        if hub_workflow_publish_request is None:
            raise bad_request("Publish payload is required.")
        if not isinstance(hub_workflow_publish_request.definition, dict):
            raise bad_request("Workflow definition must be an object.")

        dependencies = self._resolve_dependencies(hub_workflow_publish_request)
        self._ensure_dependencies_available(dependencies)

        try:
            payload = HubClient.from_settings().publish_workflow(
                hub_workflow_publish_request.to_dict()
            )
        except HubNotConfiguredError as exc:
            raise bad_request(str(exc), error="hub_not_configured") from exc
        except HubUnauthorizedError as exc:
            raise forbidden(str(exc), error="hub_unauthorized") from exc
        except HubClientError as exc:
            raise bad_request(str(exc), error="hub_request_failed") from exc
        return HubWorkflowPublishResponse.from_dict(payload)

    async def get_hub_workflow(self, workflowId: str) -> HubWorkflowDetail:
        require_roles(*WORKFLOW_VIEW_ROLES)
        try:
            payload = HubClient.from_settings().get_workflow(workflowId)
        except HubNotConfiguredError as exc:
            raise bad_request(str(exc), error="hub_not_configured") from exc
        except HubNotFoundError as exc:
            raise not_found(str(exc), error="hub_not_found") from exc
        except HubUnauthorizedError as exc:
            raise forbidden(str(exc), error="hub_unauthorized") from exc
        except HubClientError as exc:
            raise bad_request(str(exc), error="hub_request_failed") from exc
        return HubWorkflowDetail.from_dict(payload)

    async def list_hub_workflow_versions(self, workflowId: str) -> HubWorkflowVersionList:
        require_roles(*WORKFLOW_VIEW_ROLES)
        try:
            payload = HubClient.from_settings().list_workflow_versions(workflowId)
        except HubNotConfiguredError as exc:
            raise bad_request(str(exc), error="hub_not_configured") from exc
        except HubNotFoundError as exc:
            raise not_found(str(exc), error="hub_not_found") from exc
        except HubUnauthorizedError as exc:
            raise forbidden(str(exc), error="hub_unauthorized") from exc
        except HubClientError as exc:
            raise bad_request(str(exc), error="hub_request_failed") from exc
        return HubWorkflowVersionList.from_dict(payload)

    async def get_hub_workflow_version(
        self,
        workflowId: str,
        versionId: str,
    ) -> HubWorkflowVersionDetail:
        require_roles(*WORKFLOW_VIEW_ROLES)
        try:
            payload = HubClient.from_settings().get_workflow_version(workflowId, versionId)
        except HubNotConfiguredError as exc:
            raise bad_request(str(exc), error="hub_not_configured") from exc
        except HubNotFoundError as exc:
            raise not_found(str(exc), error="hub_not_found") from exc
        except HubUnauthorizedError as exc:
            raise forbidden(str(exc), error="hub_unauthorized") from exc
        except HubClientError as exc:
            raise bad_request(str(exc), error="hub_request_failed") from exc
        return HubWorkflowVersionDetail.from_dict(payload)

    async def get_hub_workflow_definition(
        self,
        workflowId: str,
        versionId: str,
    ) -> dict[str, object]:
        require_roles(*WORKFLOW_VIEW_ROLES)
        try:
            payload = HubClient.from_settings().get_workflow_definition(workflowId, versionId)
        except HubNotConfiguredError as exc:
            raise bad_request(str(exc), error="hub_not_configured") from exc
        except HubNotFoundError as exc:
            raise not_found(str(exc), error="hub_not_found") from exc
        except HubUnauthorizedError as exc:
            raise forbidden(str(exc), error="hub_unauthorized") from exc
        except HubClientError as exc:
            raise bad_request(str(exc), error="hub_request_failed") from exc
        if not isinstance(payload, dict):
            raise bad_request("Hub returned invalid workflow definition.")
        return payload

    async def import_hub_workflow(
        self,
        workflowId: str,
        hub_workflow_import_request: HubWorkflowImportRequest | None,
    ) -> HubWorkflowImportResponse:
        token = require_roles(*WORKFLOW_EDIT_ROLES)
        version_id = None
        version = None
        name_override = None
        if hub_workflow_import_request:
            version_id = hub_workflow_import_request.version_id
            version = hub_workflow_import_request.version
            name_override = hub_workflow_import_request.name

        try:
            result = hub_import_service.import_workflow(
                workflow_id=workflowId,
                version_id=version_id,
                version=version,
                actor_id=token.sub,
                name_override=name_override,
            )
        except HubImportNotFoundError as exc:
            raise not_found(exc.message, error="hub_not_found") from exc
        except HubImportError as exc:
            raise bad_request(exc.message, error="hub_import_failed", details=exc.details) from exc
        return HubWorkflowImportResponse.from_dict(result.to_dict())

    @staticmethod
    def _resolve_dependencies(
        request: HubWorkflowPublishRequest,
    ) -> list[WorkflowPackageDependency]:
        if request.dependencies:
            return [
                WorkflowPackageDependency(name=item.name, version=item.version)
                for item in request.dependencies
            ]
        definition = request.definition if isinstance(request.definition, dict) else {}
        return extract_package_dependencies(definition)

    @staticmethod
    def _ensure_dependencies_available(
        dependencies: list[WorkflowPackageDependency],
    ) -> None:
        if not dependencies:
            return
        settings = get_api_settings()
        try:
            client = HubClient.from_settings()
        except HubNotConfiguredError as exc:
            raise bad_request(str(exc), error="hub_not_configured") from exc
        missing: list[WorkflowPackageDependency] = []
        for dependency in dependencies:
            try:
                client.get_package_version(dependency.name, dependency.version)
            except HubNotFoundError:
                missing.append(dependency)
            except HubUnauthorizedError as exc:
                raise forbidden(str(exc), error="hub_unauthorized") from exc
            except HubClientError as exc:
                raise bad_request(str(exc), error="hub_request_failed") from exc
        if not missing:
            return
        details = {"packages": [item.to_dict() for item in missing]}
        if settings.hub_publish_dependency_policy == "block":
            raise bad_request(
                "Workflow dependencies are missing from Hub.",
                error="hub_dependency_missing",
                details=details,
            )
        raise bad_request(
            "Workflow dependency policy is not supported.",
            error="hub_dependency_policy_unsupported",
            details=details,
        )
