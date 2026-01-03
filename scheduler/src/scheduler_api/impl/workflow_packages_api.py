from __future__ import annotations

from typing import Optional

from scheduler_api.http.errors import bad_request, conflict, forbidden, not_found

from scheduler_api.apis.workflow_packages_api_base import BaseWorkflowPackagesApi
from scheduler_api.auth.roles import WORKFLOW_EDIT_ROLES, WORKFLOW_VIEW_ROLES, require_roles
from scheduler_api.models.clone_workflow_package_request import CloneWorkflowPackageRequest
from scheduler_api.models.get_workflow_package200_response import GetWorkflowPackage200Response
from scheduler_api.models.list_workflow_package_versions200_response import (
    ListWorkflowPackageVersions200Response,
)
from scheduler_api.models.list_workflow_packages200_response import ListWorkflowPackages200Response
from scheduler_api.models.persist_workflow201_response import PersistWorkflow201Response
from scheduler_api.models.publish_workflow200_response import PublishWorkflow200Response
from scheduler_api.models.publish_workflow_request import PublishWorkflowRequest
from scheduler_api.models.workflow import Workflow
from scheduler_api.service.workflow_packages import (
    WorkflowPackageConflictError,
    WorkflowPackageNotFoundError,
    WorkflowPackageOwnerError,
    WorkflowPackageService,
    WorkflowPackageValidationError,
    WorkflowPackageVisibilityError,
)
from scheduler_api.service.workflows import (
    WorkflowNotFoundError,
    WorkflowPermissionError,
    WorkflowValidationError,
)

_workflow_package_service = WorkflowPackageService()


class WorkflowPackagesApiImpl(BaseWorkflowPackagesApi):
    async def list_workflow_packages(
        self,
        limit: Optional[int],
        cursor: Optional[str],
        owner: Optional[str],
        visibility: Optional[str],
        search: Optional[str],
    ) -> ListWorkflowPackages200Response:
        del cursor  # cursor-based pagination reserved for future enhancement
        token = require_roles(*WORKFLOW_VIEW_ROLES)
        return _workflow_package_service.list_workflow_packages(
            limit=limit,
            owner=owner,
            visibility=visibility,
            search=search,
            requester_id=token.sub if token else None,
        )

    async def get_workflow_package(
        self,
        packageId: str,
    ) -> GetWorkflowPackage200Response:
        token = require_roles(*WORKFLOW_VIEW_ROLES)
        try:
            return _workflow_package_service.get_workflow_package(
                packageId,
                requester_id=token.sub if token else None,
            )
        except WorkflowPackageNotFoundError as exc:
            raise not_found(exc.message, error="workflow_package_not_found") from exc
        except WorkflowPackageVisibilityError as exc:
            raise forbidden(exc.message) from exc

    async def get_workflow_package_versions(
        self,
        packageId: str,
    ) -> ListWorkflowPackageVersions200Response:
        token = require_roles(*WORKFLOW_VIEW_ROLES)
        try:
            return _workflow_package_service.get_workflow_package_versions(
                packageId,
                requester_id=token.sub if token else None,
            )
        except WorkflowPackageNotFoundError as exc:
            raise not_found(exc.message, error="workflow_package_not_found") from exc
        except WorkflowPackageVisibilityError as exc:
            raise forbidden(exc.message) from exc

    async def clone_workflow_package(
        self,
        packageId: str,
        clone_workflow_package_request: Optional[CloneWorkflowPackageRequest],
    ) -> PersistWorkflow201Response:
        token = require_roles(*WORKFLOW_EDIT_ROLES)
        try:
            return await _workflow_package_service.clone_workflow_package(
                packageId,
                clone_workflow_package_request,
                actor_id=token.sub if token else None,
            )
        except WorkflowPackageNotFoundError as exc:
            raise not_found(exc.message, error="workflow_package_not_found") from exc
        except WorkflowPackageVisibilityError as exc:
            raise forbidden(exc.message) from exc
        except WorkflowValidationError as exc:
            raise bad_request(exc.message, error=exc.error) from exc
        except WorkflowPermissionError as exc:
            raise forbidden(str(exc)) from exc

    async def get_workflow_package_definition(
        self,
        packageId: str,
        versionId: str,
    ) -> Workflow:
        token = require_roles(*WORKFLOW_VIEW_ROLES)
        try:
            definition = _workflow_package_service.get_workflow_definition(
                packageId,
                version_id=versionId,
                requester_id=token.sub if token else None,
            )
        except WorkflowPackageNotFoundError as exc:
            raise not_found(exc.message, error="workflow_package_not_found") from exc
        except WorkflowPackageVisibilityError as exc:
            raise forbidden(exc.message) from exc
        except WorkflowPackageValidationError as exc:
            raise bad_request(exc.message, error=exc.error, details=exc.details) from exc
        return Workflow.from_dict(definition)

    async def publish_workflow(
        self,
        workflowId: str,
        publish_workflow_request: PublishWorkflowRequest,
    ) -> PublishWorkflow200Response:
        token = require_roles(*WORKFLOW_EDIT_ROLES)
        try:
            return _workflow_package_service.publish_workflow(
                workflowId,
                publish_workflow_request,
                actor_id=token.sub if token else None,
            )
        except WorkflowPackageValidationError as exc:
            raise bad_request(exc.message, error=exc.error, details=getattr(exc, "details", None)) from exc
        except WorkflowPackageNotFoundError as exc:
            raise not_found(exc.message, error="workflow_package_not_found") from exc
        except WorkflowPackageOwnerError as exc:
            raise forbidden(exc.message) from exc
        except WorkflowPackageConflictError as exc:
            raise conflict(exc.message) from exc
        except WorkflowNotFoundError as exc:
            raise not_found("Workflow not found.", error="workflow_not_found") from exc

    async def delete_workflow_package(
        self,
        packageId: str,
    ) -> None:
        token = require_roles(*WORKFLOW_EDIT_ROLES)
        try:
            _workflow_package_service.delete_workflow_package(
                packageId,
                actor_id=token.sub if token else None,
            )
        except WorkflowPackageNotFoundError as exc:
            raise not_found(exc.message, error="workflow_package_not_found") from exc
        except WorkflowPackageOwnerError as exc:
            raise forbidden(exc.message) from exc
