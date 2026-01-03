"""Service layer for workflow package operations."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import re
from typing import Optional
from uuid import uuid4

from sqlalchemy.exc import IntegrityError

from scheduler_api.db.models import WorkflowPackageRecord, WorkflowPackageVersionRecord
from scheduler_api.config.settings import get_api_settings
from scheduler_api.models.clone_workflow_package_request import CloneWorkflowPackageRequest
from scheduler_api.models.get_workflow_package200_response import GetWorkflowPackage200Response
from scheduler_api.models.list_workflow_package_versions200_response import (
    ListWorkflowPackageVersions200Response,
)
from scheduler_api.models.list_workflow_packages200_response import ListWorkflowPackages200Response
from scheduler_api.models.list_workflow_packages200_response_items_inner import (
    ListWorkflowPackages200ResponseItemsInner,
)
from scheduler_api.models.list_workflow_packages200_response_items_inner_latest_version import (
    ListWorkflowPackages200ResponseItemsInnerLatestVersion,
)
from scheduler_api.models.list_workflows200_response_items_inner import (
    ListWorkflows200ResponseItemsInner,
)
from scheduler_api.models.persist_workflow201_response import PersistWorkflow201Response
from scheduler_api.models.publish_workflow200_response import PublishWorkflow200Response
from scheduler_api.models.publish_workflow_request import PublishWorkflowRequest
from scheduler_api.db.session import run_in_session
from scheduler_api.repo.users import UserRepository
from scheduler_api.repo.workflow_packages import (
    WorkflowPackageRepository,
    WorkflowPackageVersionRepository,
)
from scheduler_api.repo.workflows import WorkflowRepository
from scheduler_api.service.workflows import WorkflowNotFoundError, WorkflowService
from scheduler_api.service.registry_accounts import registry_account_service
from scheduler_api.service.registry_client import (
    RegistryActor,
    RegistryClient,
    RegistryClientError,
    RegistryNotFoundError,
)
from scheduler_api.service.workflow_dependencies import extract_package_dependencies


class WorkflowPackageError(Exception):
    pass


class WorkflowPackageNotFoundError(WorkflowPackageError):
    def __init__(self, message: str = "Package not found.") -> None:
        super().__init__(message)
        self.message = message


class WorkflowPackageVisibilityError(WorkflowPackageError):
    def __init__(self, message: str = "Package is private.") -> None:
        super().__init__(message)
        self.message = message


class WorkflowPackageOwnerError(WorkflowPackageError):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class WorkflowPackageConflictError(WorkflowPackageError):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class WorkflowPackageValidationError(WorkflowPackageError):
    def __init__(self, error: str, message: str, details: dict[str, object] | None = None) -> None:
        super().__init__(message)
        self.error = error
        self.message = message
        self.details = details


class WorkflowPackageService:
    def __init__(
        self,
        *,
        package_repo: Optional[WorkflowPackageRepository] = None,
        version_repo: Optional[WorkflowPackageVersionRepository] = None,
        workflow_repo: Optional[WorkflowRepository] = None,
        users: Optional[UserRepository] = None,
        workflows: Optional[WorkflowService] = None,
    ) -> None:
        self._package_repo = package_repo or WorkflowPackageRepository()
        self._version_repo = version_repo or WorkflowPackageVersionRepository()
        self._workflow_repo = workflow_repo or WorkflowRepository()
        self._users = users or UserRepository()
        self._workflows = workflows or WorkflowService(
            repo=self._workflow_repo,
            users=self._users,
        )

    def list_workflow_packages(
        self,
        *,
        limit: Optional[int],
        owner: Optional[str],
        visibility: Optional[str],
        search: Optional[str],
        requester_id: Optional[str],
    ) -> ListWorkflowPackages200Response:
        owner_filter = owner
        if owner_filter in {None, "", "me"} and requester_id:
            owner_filter = requester_id if owner_filter == "me" else owner_filter
        page_size = limit or 50
        def _list(session):
            packages = self._package_repo.list(
                limit=page_size,
                owner_filter=owner_filter,
                requester_id=requester_id,
                visibility=visibility,
                search=search,
                session=session,
            )
            latest_versions = self._version_repo.get_latest_versions(
                [pkg.id for pkg in packages],
                session=session,
            )
            return [
                self._to_summary_model(
                    pkg,
                    latest_versions.get(pkg.id),
                    session=session,
                )
                for pkg in packages
            ]

        items = run_in_session(_list)
        return ListWorkflowPackages200Response(items=items, next_cursor=None)

    def get_workflow_package(
        self,
        package_id: str,
        *,
        requester_id: Optional[str],
    ) -> GetWorkflowPackage200Response:
        def _get(session):
            package = self._package_repo.get(package_id, session=session)
            if package is None:
                raise WorkflowPackageNotFoundError()
            self._ensure_not_deleted(package)
            self._ensure_visible(package, requester_id)
            versions = self._version_repo.list_by_package(package.id, session=session)
            version_models = [self._to_version_model(v) for v in versions]
            summary = self._to_summary_model(
                package,
                version_models[0] if version_models else None,
                session=session,
            )
            return summary, version_models

        summary, version_models = run_in_session(_get)
        return GetWorkflowPackage200Response(
            **summary.model_dump(by_alias=True),
            versions=version_models,
        )

    def get_workflow_package_versions(
        self,
        package_id: str,
        *,
        requester_id: Optional[str],
    ) -> ListWorkflowPackageVersions200Response:
        def _get(session):
            package = self._package_repo.get(package_id, session=session)
            if package is None:
                raise WorkflowPackageNotFoundError()
            self._ensure_not_deleted(package)
            self._ensure_visible(package, requester_id)
            versions = self._version_repo.list_by_package(package.id, session=session)
            return [self._to_version_model(v) for v in versions]

        items = run_in_session(_get)
        return ListWorkflowPackageVersions200Response(items=items)

    async def clone_workflow_package(
        self,
        package_id: str,
        request: Optional[CloneWorkflowPackageRequest],
        *,
        actor_id: Optional[str],
    ) -> PersistWorkflow201Response:
        payload_request = request or CloneWorkflowPackageRequest()
        def _load(session):
            package = self._package_repo.get(package_id, session=session)
            if package is None:
                raise WorkflowPackageNotFoundError()
            self._ensure_not_deleted(package)
            self._ensure_visible(package, actor_id)

            version = None
            if payload_request.version_id:
                version = self._version_repo.get_by_id(payload_request.version_id, session=session)
            elif payload_request.version:
                version = self._version_repo.get_by_version(
                    package_id=package.id,
                    version=payload_request.version,
                    session=session,
                )
            else:
                versions = self._version_repo.list_by_package(package.id, session=session)
                version = versions[0] if versions else None

            if version is None:
                raise WorkflowPackageNotFoundError("Requested package version was not found.")
            return package, version

        package, version = run_in_session(_load)

        payload = json.loads(version.definition_snapshot)
        new_workflow_id = str(uuid4())
        payload["id"] = new_workflow_id
        metadata = payload.setdefault("metadata", {})
        metadata["ownerId"] = actor_id if actor_id else metadata.get("ownerId")
        metadata["originId"] = metadata.get("originId") or version.id
        if actor_id:
            metadata["createdBy"] = actor_id
            metadata["updatedBy"] = actor_id
        if payload_request.workflow_name:
            metadata["name"] = payload_request.workflow_name

        workflow_model = ListWorkflows200ResponseItemsInner.from_dict(payload)
        return self._workflows.persist_workflow(workflow_model, actor_id=actor_id)

    def publish_workflow(
        self,
        workflow_id: str,
        request: PublishWorkflowRequest,
        *,
        actor_id: Optional[str],
    ) -> PublishWorkflow200Response:
        if not request.version:
            raise WorkflowPackageValidationError("invalid_payload", "Version is required.")

        def _publish(session):
            workflow = self._workflow_repo.get(workflow_id, session=session)
            if workflow is None:
                raise WorkflowNotFoundError(workflow_id)
            owner = workflow.owner_id or workflow.created_by
            if actor_id is None or owner != actor_id:
                raise WorkflowPackageOwnerError("Cannot publish another user's workflow.")

            workflow_payload = self._workflows.hydrate_payload(workflow, session=session)
            self._ensure_registry_dependencies(
                workflow_payload,
                actor_id=actor_id,
            )
            metadata = workflow_payload.get("metadata") if isinstance(workflow_payload, dict) else None
            owner_display_name = None
            if isinstance(metadata, dict):
                owner_name_value = metadata.get("ownerName")
                if isinstance(owner_name_value, str) and owner_name_value:
                    owner_display_name = owner_name_value
            if not owner_display_name:
                looked_up_name = self._users.get_display_name(owner, session=session)
                if looked_up_name:
                    owner_display_name = looked_up_name

            package = None
            slug = request.slug
            if request.package_id:
                package = self._package_repo.get(request.package_id, session=session)
                if package is None:
                    raise WorkflowPackageNotFoundError()
                self._ensure_not_deleted(package)
                self._ensure_owner(package, actor_id)
            elif slug:
                package = self._package_repo.get_by_slug(slug, session=session)
                if package:
                    if package.deleted_at is not None:
                        self._ensure_owner(package, actor_id)
                        package.deleted_at = None
                    self._ensure_owner(package, actor_id)

            if package is None:
                if not slug:
                    slug = self._slugify(request.display_name or workflow.name)
                package = WorkflowPackageRecord(
                    id=str(uuid4()),
                    slug=slug,
                    display_name=request.display_name or workflow.name,
                    summary=request.summary or workflow.description,
                    visibility=request.visibility or "private",
                    tags=json.dumps(request.tags) if request.tags else None,
                    owner_id=actor_id,
                    owner_name=owner_display_name,
                    created_by=actor_id,
                    updated_by=actor_id,
                )
                self._package_repo.save(package, session=session)
            else:
                if request.display_name:
                    package.display_name = request.display_name
                if request.summary is not None:
                    package.summary = request.summary
                if request.visibility:
                    package.visibility = request.visibility
                if request.tags is not None:
                    package.tags = json.dumps(request.tags)
                if owner_display_name:
                    package.owner_name = owner_display_name
                package.updated_by = actor_id
                if not package.owner_id:
                    package.owner_id = actor_id

            snapshot_image = request.preview_image or workflow.preview_image
            version_record = WorkflowPackageVersionRecord(
                id=str(uuid4()),
                package_id=package.id,
                version=request.version,
                changelog=request.changelog,
                definition_snapshot=json.dumps(workflow_payload, ensure_ascii=False),
                publisher_id=actor_id,
                preview_image=snapshot_image,
            )
            self._version_repo.save(version_record, session=session)
            return package.id, version_record.id

        try:
            package_id, version_id = run_in_session(_publish)
        except IntegrityError as exc:
            raise WorkflowPackageConflictError("Package version already exists.") from exc

        return PublishWorkflow200Response(
            package_id=package_id,
            version_id=version_id,
            version=request.version,
        )

    def get_workflow_definition(
        self,
        package_id: str,
        *,
        version_id: str,
        requester_id: Optional[str],
    ) -> dict[str, object]:
        def _get(session) -> dict[str, object]:
            package = self._package_repo.get(package_id, session=session)
            if package is None:
                raise WorkflowPackageNotFoundError()
            self._ensure_not_deleted(package)
            self._ensure_visible(package, requester_id)
            version = self._version_repo.get_by_id(version_id, session=session)
            if version is None or version.package_id != package.id:
                raise WorkflowPackageNotFoundError("Requested package version was not found.")
            try:
                return json.loads(version.definition_snapshot)
            except json.JSONDecodeError as exc:
                raise WorkflowPackageValidationError(
                    "invalid_definition",
                    "Workflow definition snapshot is invalid.",
                ) from exc

        return run_in_session(_get)

    def delete_workflow_package(self, package_id: str, *, actor_id: Optional[str]) -> None:
        def _delete(session) -> None:
            package = self._package_repo.get(package_id, session=session)
            if package is None or package.deleted_at is not None:
                raise WorkflowPackageNotFoundError()
            self._ensure_owner(package, actor_id)
            package.deleted_at = datetime.now(timezone.utc)
            return None

        run_in_session(_delete)

    @staticmethod
    def _decode_tags(tags_text: Optional[str]) -> list[str]:
        if not tags_text:
            return []
        try:
            data = json.loads(tags_text)
            if isinstance(data, list):
                return [str(item) for item in data]
        except json.JSONDecodeError:
            pass
        return []

    def _to_summary_model(
        self,
        package: WorkflowPackageRecord,
        latest_version: Optional[WorkflowPackageVersionRecord | ListWorkflowPackages200ResponseItemsInnerLatestVersion],
        *,
        session,
    ) -> ListWorkflowPackages200ResponseItemsInner:
        tags = self._decode_tags(package.tags)
        owner_identifier = package.owner_id or package.created_by
        owner_name = package.owner_name or self._users.get_display_name(owner_identifier, session=session)
        version_model = (
            latest_version
            if isinstance(latest_version, ListWorkflowPackages200ResponseItemsInnerLatestVersion)
            else self._to_version_model(latest_version) if latest_version else None
        )
        return ListWorkflowPackages200ResponseItemsInner(
            id=package.id,
            slug=package.slug,
            display_name=package.display_name,
            summary=package.summary,
            visibility=package.visibility,
            tags=tags if tags else None,
            owner_id=owner_identifier,
            owner_name=owner_name,
            updated_at=package.updated_at,
            latest_version=version_model,
            preview_image=version_model.preview_image if version_model else None,
        )

    @staticmethod
    def _to_version_model(
        record: WorkflowPackageVersionRecord,
    ) -> ListWorkflowPackages200ResponseItemsInnerLatestVersion:
        return ListWorkflowPackages200ResponseItemsInnerLatestVersion(
            id=record.id,
            version=record.version,
            changelog=record.changelog,
            published_at=record.published_at,
            publisher_id=record.publisher_id,
            preview_image=record.preview_image,
        )

    @staticmethod
    def _ensure_not_deleted(package: WorkflowPackageRecord) -> None:
        if package.deleted_at is not None:
            raise WorkflowPackageNotFoundError()

    @staticmethod
    def _ensure_visible(
        package: WorkflowPackageRecord,
        requester_id: Optional[str],
    ) -> None:
        if package.visibility == "public":
            return
        if requester_id and package.owner_id == requester_id:
            return
        raise WorkflowPackageVisibilityError()

    @staticmethod
    def _ensure_owner(
        package: WorkflowPackageRecord,
        requester_id: Optional[str],
    ) -> None:
        if requester_id and package.owner_id == requester_id:
            return
        raise WorkflowPackageOwnerError("Only the owner can modify this package.")

    @staticmethod
    def _slugify(value: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
        return slug or uuid4().hex[:10]

    def _resolve_registry_actor(self, actor_id: Optional[str]) -> RegistryActor | None:
        if not actor_id:
            return None
        link = registry_account_service.get_by_user_id(actor_id)
        return RegistryActor(
            platform_user_id=actor_id,
            registry_user_id=link.registry_user_id if link else None,
            registry_username=link.registry_username if link else None,
        )

    def _ensure_registry_dependencies(
        self,
        workflow_payload: dict[str, object],
        *,
        actor_id: Optional[str],
    ) -> None:
        settings = get_api_settings()
        if settings.registry_publish_dependency_policy != "block":
            return
        dependencies = extract_package_dependencies(workflow_payload)
        if not dependencies:
            return
        if not settings.registry_base_url:
            raise WorkflowPackageValidationError(
                "registry_not_configured",
                "Registry base URL is not configured.",
            )
        client = RegistryClient.from_settings()
        actor = self._resolve_registry_actor(actor_id)
        missing = []
        for dependency in dependencies:
            try:
                client.get_package_detail(
                    dependency.name,
                    version=dependency.version,
                    actor=actor,
                )
            except RegistryNotFoundError:
                missing.append(dependency.to_dict())
            except RegistryClientError as exc:
                raise WorkflowPackageValidationError(
                    "registry_error",
                    str(exc),
                ) from exc
        if missing:
            raise WorkflowPackageValidationError(
                "missing_dependencies",
                "Missing package dependencies.",
                details={"missingPackages": missing},
            )


__all__ = [
    "WorkflowPackageService",
    "WorkflowPackageError",
    "WorkflowPackageNotFoundError",
    "WorkflowPackageVisibilityError",
    "WorkflowPackageOwnerError",
    "WorkflowPackageConflictError",
    "WorkflowPackageValidationError",
]
