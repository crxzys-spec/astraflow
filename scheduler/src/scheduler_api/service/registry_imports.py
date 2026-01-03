"""Service for importing registry workflows into the platform."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from uuid import uuid4

from scheduler_api.config.settings import get_api_settings
from scheduler_api.models.list_workflows200_response_items_inner import (
    ListWorkflows200ResponseItemsInner,
)
from scheduler_api.service.registry_accounts import registry_account_service
from scheduler_api.service.registry_client import (
    RegistryActor,
    RegistryClient,
    RegistryClientError,
    RegistryNotConfiguredError,
    RegistryNotFoundError,
)
from scheduler_api.service.registry_mirror import RegistryMirrorError, registry_mirror_service
from scheduler_api.service.workflow_dependencies import WorkflowPackageDependency, extract_package_dependencies
from scheduler_api.service.workflows import WorkflowService


class RegistryImportError(Exception):
    """Raised when registry import fails."""

    def __init__(self, message: str, details: dict[str, object] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details


class RegistryImportNotFoundError(RegistryImportError):
    """Raised when registry resources are missing."""


@dataclass(frozen=True)
class RegistryWorkflowImportResult:
    workflow_id: str
    package_id: str
    version_id: str
    dependencies: list[WorkflowPackageDependency]
    pulled_packages: list[WorkflowPackageDependency]

    def to_dict(self) -> dict[str, object]:
        return {
            "workflowId": self.workflow_id,
            "packageId": self.package_id,
            "versionId": self.version_id,
            "dependencies": [dep.to_dict() for dep in self.dependencies],
            "pulledPackages": [dep.to_dict() for dep in self.pulled_packages],
        }


class RegistryImportService:
    def __init__(self, workflows: WorkflowService | None = None) -> None:
        self._workflows = workflows or WorkflowService()

    def import_workflow(
        self,
        *,
        package_id: str,
        version_id: Optional[str],
        version: Optional[str],
        actor_id: Optional[str],
        name_override: Optional[str],
    ) -> RegistryWorkflowImportResult:
        settings = get_api_settings()
        if not settings.registry_base_url:
            raise RegistryImportError("Registry base URL is not configured.")

        actor = self._resolve_registry_actor(actor_id)
        client = RegistryClient.from_settings()

        try:
            package_detail = client.get_workflow_package(package_id, actor=actor)
        except RegistryNotFoundError as exc:
            raise RegistryImportNotFoundError("Workflow package not found in registry.") from exc
        except RegistryClientError as exc:
            raise RegistryImportError(str(exc)) from exc
        except RegistryNotConfiguredError as exc:
            raise RegistryImportError(str(exc)) from exc

        selected_version_id = self._resolve_version_id(
            package_detail,
            version_id=version_id,
            version=version,
        )
        if not selected_version_id:
            raise RegistryImportNotFoundError("Workflow package version not found.")

        try:
            definition = client.get_workflow_definition(
                package_id,
                version_id=selected_version_id,
                actor=actor,
            )
        except RegistryNotFoundError as exc:
            raise RegistryImportNotFoundError("Workflow definition not found in registry.") from exc
        except RegistryClientError as exc:
            raise RegistryImportError(str(exc)) from exc

        dependencies = extract_package_dependencies(definition)
        pulled_packages = self._pull_dependencies(
            dependencies=dependencies,
            actor=actor,
        )

        new_definition = dict(definition)
        new_definition["id"] = str(uuid4())
        metadata = new_definition.get("metadata")
        if not isinstance(metadata, dict):
            metadata = {}
        if name_override:
            metadata["name"] = name_override
        if selected_version_id:
            metadata.setdefault("originId", selected_version_id)
        if actor_id:
            metadata["ownerId"] = actor_id
            metadata["createdBy"] = actor_id
            metadata["updatedBy"] = actor_id
        new_definition["metadata"] = metadata

        workflow_model = ListWorkflows200ResponseItemsInner.from_dict(new_definition)
        persisted = self._workflows.persist_workflow(workflow_model, actor_id=actor_id)

        return RegistryWorkflowImportResult(
            workflow_id=persisted.workflow_id,
            package_id=package_id,
            version_id=selected_version_id,
            dependencies=dependencies,
            pulled_packages=pulled_packages,
        )

    def _resolve_registry_actor(self, actor_id: Optional[str]) -> RegistryActor | None:
        if not actor_id:
            return None
        link = registry_account_service.get_by_user_id(actor_id)
        return RegistryActor(
            platform_user_id=actor_id,
            registry_user_id=link.registry_user_id if link else None,
            registry_username=link.registry_username if link else None,
        )

    @staticmethod
    def _resolve_version_id(
        package_detail: dict[str, object],
        *,
        version_id: Optional[str],
        version: Optional[str],
    ) -> Optional[str]:
        versions = package_detail.get("versions")
        if not isinstance(versions, list):
            return version_id
        if version_id:
            for item in versions:
                if isinstance(item, dict) and item.get("id") == version_id:
                    return version_id
        if version:
            for item in versions:
                if isinstance(item, dict) and item.get("version") == version:
                    return item.get("id") if isinstance(item.get("id"), str) else None
        latest = package_detail.get("latestVersion")
        if isinstance(latest, dict):
            latest_id = latest.get("id")
            if isinstance(latest_id, str):
                return latest_id
        return version_id

    def _pull_dependencies(
        self,
        *,
        dependencies: list[WorkflowPackageDependency],
        actor: RegistryActor | None,
    ) -> list[WorkflowPackageDependency]:
        settings = get_api_settings()
        if settings.registry_package_pull_policy != "auto":
            return []
        pulled: list[WorkflowPackageDependency] = []
        for dependency in dependencies:
            try:
                registry_mirror_service.ensure_package(
                    name=dependency.name,
                    version=dependency.version,
                    actor=actor,
                )
                registry_mirror_service.install_to_catalog(
                    name=dependency.name,
                    version=dependency.version,
                )
                pulled.append(dependency)
            except RegistryMirrorError as exc:
                raise RegistryImportError(
                    f"Failed to pull package {dependency.name}@{dependency.version}.",
                    details={"package": dependency.to_dict()},
                ) from exc
        return pulled


registry_import_service = RegistryImportService()

__all__ = [
    "RegistryImportError",
    "RegistryImportNotFoundError",
    "RegistryWorkflowImportResult",
    "RegistryImportService",
    "registry_import_service",
]
