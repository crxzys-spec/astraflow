from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.exc import IntegrityError

from scheduler_api.apis.workflow_packages_api_base import BaseWorkflowPackagesApi
from scheduler_api.auth.roles import WORKFLOW_EDIT_ROLES, WORKFLOW_VIEW_ROLES, require_roles
from scheduler_api.db.models import (
    WorkflowPackageRecord,
    WorkflowPackageVersionRecord,
    WorkflowRecord,
)
from scheduler_api.db.session import SessionLocal
from scheduler_api.impl.workflows_api import WorkflowsApiImpl
from scheduler_api.models.list_workflows200_response_items_inner import (
    ListWorkflows200ResponseItemsInner,
)
from scheduler_api.models.persist_workflow201_response import PersistWorkflow201Response
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
from scheduler_api.models.publish_workflow200_response import PublishWorkflow200Response
from scheduler_api.models.publish_workflow_request import PublishWorkflowRequest


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
        owner_filter = owner
        if owner_filter in {None, "", "me"} and token:
            owner_filter = token.sub if owner_filter == "me" else owner_filter
        page_size = limit or 50

        with SessionLocal() as session:
            stmt = select(WorkflowPackageRecord).order_by(
                WorkflowPackageRecord.updated_at.desc()
            )
            stmt = stmt.limit(page_size)
            stmt = stmt.where(WorkflowPackageRecord.deleted_at.is_(None))

            if owner_filter:
                stmt = stmt.where(WorkflowPackageRecord.owner_id == owner_filter)
            else:
                stmt = stmt.where(
                    or_(
                        WorkflowPackageRecord.visibility == "public",
                        WorkflowPackageRecord.owner_id == (token.sub if token else None),
                    )
                )

            if visibility:
                stmt = stmt.where(WorkflowPackageRecord.visibility == visibility)

            if search:
                pattern = f"%{search.lower()}%"
                stmt = stmt.where(
                    or_(
                        func.lower(WorkflowPackageRecord.slug).like(pattern),
                        func.lower(WorkflowPackageRecord.display_name).like(pattern),
                        func.lower(WorkflowPackageRecord.summary).like(pattern),
                    )
                )

            packages = session.execute(stmt).scalars().all()
            latest_versions = self._load_latest_versions(session, [pkg.id for pkg in packages])

        items = [
            self._to_summary_model(pkg, latest_versions.get(pkg.id)) for pkg in packages
        ]
        return ListWorkflowPackages200Response(items=items, next_cursor=None)

    async def get_workflow_package(
        self,
        packageId: str,
    ) -> GetWorkflowPackage200Response:
        token = require_roles(*WORKFLOW_VIEW_ROLES)
        with SessionLocal() as session:
            package = session.get(WorkflowPackageRecord, packageId)
            if package is None:
                raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Package not found.")
            self._ensure_not_deleted(package)
            self._ensure_visible(package, token.sub if token else None)
            versions = (
                session.execute(
                    select(WorkflowPackageVersionRecord)
                    .where(WorkflowPackageVersionRecord.package_id == package.id)
                    .order_by(WorkflowPackageVersionRecord.published_at.desc())
                )
                .scalars()
                .all()
            )

        version_models = [self._to_version_model(v) for v in versions]
        summary = self._to_summary_model(package, version_models[0] if version_models else None)
        return GetWorkflowPackage200Response(
            **summary.model_dump(by_alias=True),
            versions=version_models,
        )

    async def get_workflow_package_versions(
        self,
        packageId: str,
    ) -> ListWorkflowPackageVersions200Response:
        token = require_roles(*WORKFLOW_VIEW_ROLES)
        with SessionLocal() as session:
            package = session.get(WorkflowPackageRecord, packageId)
            if package is None:
                raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Package not found.")
            self._ensure_not_deleted(package)
            self._ensure_visible(package, token.sub if token else None)
            versions = (
                session.execute(
                    select(WorkflowPackageVersionRecord)
                    .where(WorkflowPackageVersionRecord.package_id == package.id)
                    .order_by(WorkflowPackageVersionRecord.published_at.desc())
                )
                .scalars()
                .all()
            )

        return ListWorkflowPackageVersions200Response(
            items=[self._to_version_model(v) for v in versions]
        )

    async def clone_workflow_package(
        self,
        packageId: str,
        clone_workflow_package_request: Optional[CloneWorkflowPackageRequest],
    ) -> PersistWorkflow201Response:
        token = require_roles(*WORKFLOW_EDIT_ROLES)
        request = clone_workflow_package_request or CloneWorkflowPackageRequest()
        with SessionLocal() as session:
            package = session.get(WorkflowPackageRecord, packageId)
            if package is None:
                raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Package not found.")
            self._ensure_not_deleted(package)
            self._ensure_visible(package, token.sub if token else None)

            version_stmt = select(WorkflowPackageVersionRecord).where(
                WorkflowPackageVersionRecord.package_id == package.id
            )
            if request.version_id:
                version_stmt = version_stmt.where(
                    WorkflowPackageVersionRecord.id == request.version_id
                )
            elif request.version:
                version_stmt = version_stmt.where(
                    WorkflowPackageVersionRecord.version == request.version
                )
            version_stmt = version_stmt.order_by(
                WorkflowPackageVersionRecord.published_at.desc()
            )
            version = session.execute(version_stmt).scalars().first()
            if version is None:
                raise HTTPException(
                    status.HTTP_404_NOT_FOUND,
                    detail="Requested package version was not found.",
                )

        payload = json.loads(version.definition_snapshot)
        new_workflow_id = str(uuid4())
        payload["id"] = new_workflow_id
        metadata = payload.setdefault("metadata", {})
        metadata["ownerId"] = token.sub if token else metadata.get("ownerId")
        metadata["originId"] = metadata.get("originId") or version.id
        if token:
            metadata["createdBy"] = token.sub
            metadata["updatedBy"] = token.sub
        if request.workflow_name:
            metadata["name"] = request.workflow_name

        workflow_model = ListWorkflows200ResponseItemsInner.from_dict(payload)
        persist_impl = WorkflowsApiImpl()
        return await persist_impl.persist_workflow(workflow_model, None)

    async def publish_workflow(
        self,
        workflowId: str,
        publish_workflow_request: PublishWorkflowRequest,
    ) -> PublishWorkflow200Response:
        token = require_roles(*WORKFLOW_EDIT_ROLES)
        request = publish_workflow_request
        if not request.version:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail={"error": "invalid_payload", "message": "Version is required."},
            )

        with SessionLocal() as session:
            workflow = session.get(WorkflowRecord, workflowId)
            if workflow is None:
                raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Workflow not found.")
            owner = workflow.owner_id or workflow.created_by
            if token is None or owner != token.sub:
                raise HTTPException(
                    status.HTTP_403_FORBIDDEN,
                    detail={"error": "forbidden", "message": "Cannot publish another user's workflow."},
                )

            workflow_payload = WorkflowsApiImpl._hydrate_payload(workflow)
            metadata = workflow_payload.get("metadata") if isinstance(workflow_payload, dict) else None
            owner_display_name = None
            if isinstance(metadata, dict):
                owner_name_value = metadata.get("ownerName")
                if isinstance(owner_name_value, str) and owner_name_value:
                    owner_display_name = owner_name_value
            if not owner_display_name:
                looked_up_name = WorkflowsApiImpl._lookup_user_name(owner)
                if looked_up_name:
                    owner_display_name = looked_up_name

            package = None
            slug = request.slug
            if request.package_id:
                package = session.get(WorkflowPackageRecord, request.package_id)
                if package is None:
                    raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Package not found.")
                self._ensure_not_deleted(package)
                self._ensure_owner(package, token.sub)
            elif slug:
                package = session.execute(
                    select(WorkflowPackageRecord).where(WorkflowPackageRecord.slug == slug)
                ).scalar_one_or_none()
                if package:
                    if package.deleted_at is not None:
                        self._ensure_owner(package, token.sub)
                        package.deleted_at = None
                    self._ensure_owner(package, token.sub)

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
                    owner_id=token.sub,
                    owner_name=owner_display_name,
                    created_by=token.sub,
                    updated_by=token.sub,
                )
                session.add(package)
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
                package.updated_by = token.sub
                if not package.owner_id:
                    package.owner_id = token.sub

            snapshot_image = request.preview_image or workflow.preview_image
            version_record = WorkflowPackageVersionRecord(
                id=str(uuid4()),
                package_id=package.id,
                version=request.version,
                changelog=request.changelog,
                definition_snapshot=json.dumps(workflow_payload, ensure_ascii=False),
                publisher_id=token.sub,
                preview_image=snapshot_image,
            )
            session.add(version_record)

            package_id = package.id
            version_id = version_record.id
            try:
                session.commit()
            except IntegrityError as exc:
                session.rollback()
                raise HTTPException(
                    status.HTTP_409_CONFLICT,
                    detail={"error": "conflict", "message": "Package version already exists."},
                ) from exc

        return PublishWorkflow200Response(
            package_id=package_id,
            version_id=version_id,
            version=request.version,
        )

    async def delete_workflow_package(
        self,
        packageId: str,
    ) -> None:
        token = require_roles(*WORKFLOW_EDIT_ROLES)
        with SessionLocal() as session:
            package = session.get(WorkflowPackageRecord, packageId)
            if package is None or package.deleted_at is not None:
                raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Package not found.")
            self._ensure_owner(package, token.sub if token else None)
            package.deleted_at = datetime.now(timezone.utc)
            session.commit()

    @staticmethod
    def _load_latest_versions(
        session, package_ids: list[str]
    ) -> dict[str, ListWorkflowPackages200ResponseItemsInnerLatestVersion]:
        if not package_ids:
            return {}
        stmt = (
            select(WorkflowPackageVersionRecord)
            .where(WorkflowPackageVersionRecord.package_id.in_(package_ids))
            .order_by(
                WorkflowPackageVersionRecord.package_id,
                WorkflowPackageVersionRecord.published_at.desc(),
            )
        )
        rows = session.execute(stmt).scalars().all()
        latest: dict[str, ListWorkflowPackages200ResponseItemsInnerLatestVersion] = {}
        for row in rows:
            if row.package_id not in latest:
                latest[row.package_id] = WorkflowPackagesApiImpl._to_version_model(row)
        return latest

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

    @staticmethod
    def _to_summary_model(
        package: WorkflowPackageRecord,
        latest_version: Optional[ListWorkflowPackages200ResponseItemsInnerLatestVersion],
    ) -> ListWorkflowPackages200ResponseItemsInner:
        tags = WorkflowPackagesApiImpl._decode_tags(package.tags)
        owner_identifier = package.owner_id or package.created_by
        owner_name = package.owner_name or WorkflowsApiImpl._lookup_user_name(owner_identifier)
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
            latest_version=latest_version,
            preview_image=latest_version.preview_image if latest_version else None,
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
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                detail="Package not found.",
            )

    @staticmethod
    def _ensure_visible(package: WorkflowPackageRecord, requester_id: Optional[str]) -> None:
        if package.visibility == "public":
            return
        if requester_id and package.owner_id == requester_id:
            return
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail={"error": "forbidden", "message": "Package is private."},
        )

    @staticmethod
    def _ensure_owner(package: WorkflowPackageRecord, requester_id: Optional[str]) -> None:
        if requester_id and package.owner_id == requester_id:
            return
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail={"error": "forbidden", "message": "Only the owner can modify this package."},
        )

    @staticmethod
    def _slugify(value: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
        return slug or uuid4().hex[:10]
