from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from hub_api.db.models import HubWorkflow, HubWorkflowVersion
from hub_api.db.session import SessionLocal
from hub_api.repo.common import _now

DEFAULT_VISIBILITY = "public"

def _workflow_record_from_model(
    workflow: HubWorkflow,
    *,
    include_versions: bool,
) -> dict[str, Any]:
    versions_map: dict[str, dict[str, Any]] = {}
    if include_versions:
        for version in workflow.versions:
            versions_map[version.id] = _workflow_version_record_from_model(version)
    return {
        "id": workflow.id,
        "name": workflow.name,
        "summary": workflow.summary,
        "description": workflow.description,
        "tags": workflow.tags,
        "ownerId": workflow.owner_id,
        "ownerName": workflow.owner_name,
        "updatedAt": workflow.updated_at,
        "visibility": workflow.visibility,
        "previewImage": workflow.preview_image,
        "versions": versions_map,
        "latestVersion": workflow.latest_version,
    }

def _workflow_version_record_from_model(version: HubWorkflowVersion) -> dict[str, Any]:
    return {
        "id": version.id,
        "version": version.version,
        "summary": version.summary,
        "description": version.description,
        "tags": version.tags,
        "previewImage": version.preview_image,
        "dependencies": version.dependencies,
        "publishedAt": version.published_at,
        "publisherId": version.publisher_id,
        "definition": version.definition,
        "changelog": version.changelog,
    }

def _load_workflow(
    session,
    workflow_id: str,
    *,
    include_versions: bool,
) -> HubWorkflow | None:
    stmt = select(HubWorkflow).where(HubWorkflow.id == workflow_id)
    if include_versions:
        stmt = stmt.options(selectinload(HubWorkflow.versions))
    return session.execute(stmt).scalar_one_or_none()

def list_workflows() -> list[dict[str, Any]]:
    with SessionLocal() as session:
        workflows = session.execute(select(HubWorkflow)).scalars().all()
        return [
            _workflow_record_from_model(workflow, include_versions=False)
            for workflow in workflows
        ]

def get_workflow_record(workflow_id: str) -> dict[str, Any] | None:
    with SessionLocal() as session:
        workflow = _load_workflow(session, workflow_id, include_versions=False)
        if not workflow:
            return None
        return _workflow_record_from_model(workflow, include_versions=False)

def publish_workflow_version(
    *,
    workflow_id: str | None,
    name: str,
    version: str,
    summary: str | None,
    description: str | None,
    tags: list[str] | None,
    visibility: str,
    preview_image: str | None,
    dependencies: list[dict[str, Any]] | None,
    definition: dict[str, Any],
    publisher_id: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    with SessionLocal() as session:
        workflow = None
        if workflow_id:
            workflow = _load_workflow(session, workflow_id, include_versions=True)
        if workflow is None:
            workflow_id = workflow_id or str(uuid4())
            now = _now()
            workflow = HubWorkflow(
                id=workflow_id,
                name=name,
                summary=summary,
                description=description,
                tags=tags,
                owner_id=publisher_id,
                owner_name=publisher_id,
                updated_at=now,
                created_at=now,
                visibility=visibility,
                preview_image=preview_image,
                latest_version=None,
            )
            session.add(workflow)
            session.flush()
        else:
            if name:
                workflow.name = name
            if summary is not None:
                workflow.summary = summary
            if description is not None:
                workflow.description = description
            if tags is not None:
                workflow.tags = tags
            if preview_image is not None:
                workflow.preview_image = preview_image
            workflow.visibility = visibility
            workflow.updated_at = _now()

        existing = session.execute(
            select(HubWorkflowVersion).where(
                HubWorkflowVersion.workflow_id == workflow.id,
                HubWorkflowVersion.version == version,
            )
        ).scalar_one_or_none()
        if existing:
            raise ValueError("workflow_version_exists")

        now = _now()
        version_id = str(uuid4())
        version_record = HubWorkflowVersion(
            id=version_id,
            workflow_id=workflow.id,
            version=version,
            summary=summary,
            description=description,
            tags=tags,
            preview_image=preview_image,
            dependencies=dependencies,
            published_at=now,
            publisher_id=publisher_id,
            definition=definition,
            changelog=None,
        )
        session.add(version_record)
        workflow.latest_version = version
        workflow.updated_at = now
        session.commit()
        session.refresh(workflow)
        session.refresh(version_record)
        record = _workflow_record_from_model(workflow, include_versions=False)
        version_payload = _workflow_version_record_from_model(version_record)

    return record, version_payload

def list_workflow_versions(workflow_id: str) -> list[dict[str, Any]]:
    with SessionLocal() as session:
        workflow = _load_workflow(session, workflow_id, include_versions=False)
        if not workflow:
            raise ValueError("workflow_not_found")
        versions = session.execute(
            select(HubWorkflowVersion).where(HubWorkflowVersion.workflow_id == workflow.id)
        ).scalars().all()
        fallback_time = datetime.min.replace(tzinfo=timezone.utc)
        versions.sort(key=lambda item: item.published_at or fallback_time, reverse=True)
        return [_workflow_version_record_from_model(item) for item in versions]

def get_workflow_version_record(workflow_id: str, version_id: str) -> dict[str, Any] | None:
    with SessionLocal() as session:
        workflow = _load_workflow(session, workflow_id, include_versions=False)
        if not workflow:
            return None
        record = session.execute(
            select(HubWorkflowVersion).where(
                HubWorkflowVersion.workflow_id == workflow.id,
                HubWorkflowVersion.id == version_id,
            )
        ).scalar_one_or_none()
        if record is None:
            return None
        return _workflow_version_record_from_model(record)

def get_workflow_definition(workflow_id: str, version_id: str) -> dict[str, Any] | None:
    with SessionLocal() as session:
        workflow = _load_workflow(session, workflow_id, include_versions=False)
        if not workflow:
            return None
        record = session.execute(
            select(HubWorkflowVersion.definition).where(
                HubWorkflowVersion.workflow_id == workflow.id,
                HubWorkflowVersion.id == version_id,
            )
        ).scalar_one_or_none()
        if record is None:
            return None
        return record if isinstance(record, dict) else None
