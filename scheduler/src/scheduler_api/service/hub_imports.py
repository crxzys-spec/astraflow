"""Service for importing Hub workflows into the platform."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from uuid import uuid4

from scheduler_api.config.settings import get_api_settings
from scheduler_api.models.list_workflows200_response_items_inner import (
    ListWorkflows200ResponseItemsInner,
)
from scheduler_api.service.hub_client import HubClient, HubClientError, HubNotFoundError
from scheduler_api.service.hub_mirror import HubMirrorError, hub_mirror_service
from scheduler_api.service.workflow_dependencies import WorkflowPackageDependency, extract_package_dependencies
from scheduler_api.service.workflows import WorkflowService


class HubImportError(Exception):
    """Raised when Hub import fails."""

    def __init__(self, message: str, details: dict[str, object] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details


class HubImportNotFoundError(HubImportError):
    """Raised when Hub resources are missing."""


@dataclass(frozen=True)
class HubWorkflowImportResult:
    workflow_id: str
    workflow_source_id: str
    version_id: str
    dependencies: list[WorkflowPackageDependency]
    pulled_packages: list[WorkflowPackageDependency]

    def to_dict(self) -> dict[str, object]:
        return {
            "workflowId": self.workflow_id,
            "workflowSourceId": self.workflow_source_id,
            "versionId": self.version_id,
            "dependencies": [dep.to_dict() for dep in self.dependencies],
            "pulledPackages": [dep.to_dict() for dep in self.pulled_packages],
        }


class HubImportService:
    def __init__(self, workflows: WorkflowService | None = None) -> None:
        self._workflows = workflows or WorkflowService()

    def import_workflow(
        self,
        *,
        workflow_id: str,
        version_id: Optional[str],
        version: Optional[str],
        actor_id: Optional[str],
        name_override: Optional[str],
    ) -> HubWorkflowImportResult:
        settings = get_api_settings()
        if not settings.hub_base_url:
            raise HubImportError("Hub base URL is not configured.")

        client = HubClient.from_settings()
        try:
            versions_payload = client.list_workflow_versions(workflow_id)
        except HubNotFoundError as exc:
            raise HubImportNotFoundError("Workflow not found in Hub.") from exc
        except HubClientError as exc:
            raise HubImportError(str(exc)) from exc

        selected_version_id = self._resolve_version_id(
            versions_payload,
            version_id=version_id,
            version=version,
        )
        if not selected_version_id:
            raise HubImportNotFoundError("Workflow version not found in Hub.")

        try:
            definition = client.get_workflow_definition(
                workflow_id,
                selected_version_id,
            )
        except HubNotFoundError as exc:
            raise HubImportNotFoundError("Workflow definition not found in Hub.") from exc
        except HubClientError as exc:
            raise HubImportError(str(exc)) from exc

        if not isinstance(definition, dict):
            raise HubImportError("Hub returned invalid workflow definition.")

        dependencies = extract_package_dependencies(definition)
        pulled_packages = self._pull_dependencies(dependencies=dependencies)

        new_definition = dict(definition)
        new_definition["id"] = str(uuid4())
        metadata = new_definition.get("metadata")
        if not isinstance(metadata, dict):
            metadata = {}
        if name_override:
            metadata["name"] = name_override
        else:
            existing_name = metadata.get("name")
            if not isinstance(existing_name, str) or not existing_name.strip():
                fallback_name = self._resolve_workflow_name(client, workflow_id)
                metadata["name"] = fallback_name or workflow_id
        metadata.setdefault("originId", selected_version_id)
        if actor_id:
            metadata["ownerId"] = actor_id
            metadata["createdBy"] = actor_id
            metadata["updatedBy"] = actor_id
        new_definition["metadata"] = metadata

        workflow_model = ListWorkflows200ResponseItemsInner.from_dict(new_definition)
        persisted = self._workflows.persist_workflow(workflow_model, actor_id=actor_id)

        return HubWorkflowImportResult(
            workflow_id=persisted.workflow_id,
            workflow_source_id=workflow_id,
            version_id=selected_version_id,
            dependencies=dependencies,
            pulled_packages=pulled_packages,
        )

    @staticmethod
    def _resolve_version_id(
        payload: dict[str, object],
        *,
        version_id: Optional[str],
        version: Optional[str],
    ) -> Optional[str]:
        items = payload.get("items")
        if not isinstance(items, list):
            return version_id
        if version_id:
            for item in items:
                if isinstance(item, dict) and item.get("id") == version_id:
                    return version_id
        if version:
            for item in items:
                if isinstance(item, dict) and item.get("version") == version:
                    return item.get("id") if isinstance(item.get("id"), str) else None
        if items:
            latest = items[0]
            if isinstance(latest, dict):
                latest_id = latest.get("id")
                if isinstance(latest_id, str):
                    return latest_id
        return version_id

    @staticmethod
    def _pull_dependencies(
        *,
        dependencies: list[WorkflowPackageDependency],
    ) -> list[WorkflowPackageDependency]:
        settings = get_api_settings()
        if settings.hub_package_pull_policy != "auto":
            return []
        pulled: list[WorkflowPackageDependency] = []
        for dependency in dependencies:
            try:
                hub_mirror_service.ensure_package(
                    name=dependency.name,
                    version=dependency.version,
                )
                hub_mirror_service.install_to_catalog(
                    name=dependency.name,
                    version=dependency.version,
                )
                pulled.append(dependency)
            except HubMirrorError as exc:
                raise HubImportError(
                    f"Failed to pull package {dependency.name}@{dependency.version}.",
                    details={"package": dependency.to_dict()},
                ) from exc
        return pulled

    @staticmethod
    def _resolve_workflow_name(client: HubClient, workflow_id: str) -> Optional[str]:
        try:
            detail = client.get_workflow(workflow_id)
        except HubClientError:
            return None
        name = detail.get("name")
        if isinstance(name, str) and name.strip():
            return name
        return None


hub_import_service = HubImportService()

__all__ = [
    "HubImportError",
    "HubImportNotFoundError",
    "HubWorkflowImportResult",
    "HubImportService",
    "hub_import_service",
]
