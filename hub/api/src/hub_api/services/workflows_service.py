from __future__ import annotations

from datetime import datetime, timezone
from math import ceil

from fastapi import HTTPException, status

from hub_api.repo.audit import record_audit_event
from hub_api.repo.workflows import (
    DEFAULT_VISIBILITY,
    get_workflow_definition,
    get_workflow_record,
    get_workflow_version_record,
    list_workflow_versions,
    list_workflows,
    publish_workflow_version,
)
from hub_api.repo.packages import get_package_version_record
from hub_api.models.hub_workflow_detail import HubWorkflowDetail
from hub_api.models.hub_workflow_summary import HubWorkflowSummary
from hub_api.models.page_meta import PageMeta
from hub_api.models.workflow_list_response import WorkflowListResponse
from hub_api.models.workflow_publish_request import WorkflowPublishRequest
from hub_api.models.workflow_publish_response import WorkflowPublishResponse
from hub_api.models.workflow_version_detail import WorkflowVersionDetail
from hub_api.models.workflow_version_list import WorkflowVersionList
from hub_api.models.workflow_version_summary import WorkflowVersionSummary
from hub_api.models.visibility import Visibility
from hub_api.security_api import get_current_actor, is_admin, require_actor


def _normalize(value: str | None) -> str:
    return value.lower().strip() if value else ""


def _match_query(record: dict, query: str) -> bool:
    if not query:
        return True
    candidates = [
        record.get("name"),
        record.get("summary"),
        record.get("description"),
        record.get("ownerName"),
    ]
    query_lower = query.lower()
    return any(isinstance(item, str) and query_lower in item.lower() for item in candidates)


def _match_tag(record: dict, tag: str) -> bool:
    if not tag:
        return True
    tags = record.get("tags")
    if not isinstance(tags, list):
        return False
    tag_lower = tag.lower()
    return any(isinstance(item, str) and item.lower() == tag_lower for item in tags)


def _match_owner(record: dict, owner: str) -> bool:
    if not owner:
        return True
    owner_lower = owner.lower()
    owner_id = record.get("ownerId")
    owner_name = record.get("ownerName")
    if isinstance(owner_id, str) and owner_id.lower() == owner_lower:
        return True
    if isinstance(owner_name, str) and owner_name.lower() == owner_lower:
        return True
    return False


def _paginate(items: list[dict], page: int, page_size: int) -> tuple[list[dict], PageMeta]:
    total = len(items)
    total_pages = ceil(total / page_size) if total else 0
    start = (page - 1) * page_size
    end = start + page_size
    slice_items = items[start:end] if start < total else []
    meta = PageMeta(
        page=page,
        pageSize=page_size,
        total=total,
        totalPages=total_pages,
    )
    return slice_items, meta


def _summary_from_record(record: dict) -> HubWorkflowSummary:
    payload = {
        "id": record.get("id"),
        "name": record.get("name"),
        "summary": record.get("summary"),
        "tags": record.get("tags"),
        "ownerId": record.get("ownerId"),
        "ownerName": record.get("ownerName"),
        "updatedAt": record.get("updatedAt"),
        "latestVersion": record.get("latestVersion"),
        "visibility": record.get("visibility"),
    }
    return HubWorkflowSummary.from_dict(payload)


def _detail_from_record(record: dict) -> HubWorkflowDetail:
    payload = {
        "id": record.get("id"),
        "name": record.get("name"),
        "summary": record.get("summary"),
        "description": record.get("description"),
        "tags": record.get("tags"),
        "ownerId": record.get("ownerId"),
        "ownerName": record.get("ownerName"),
        "updatedAt": record.get("updatedAt"),
        "previewImage": record.get("previewImage"),
        "visibility": record.get("visibility"),
    }
    return HubWorkflowDetail.from_dict(payload)


def _version_summary_from_record(record: dict) -> WorkflowVersionSummary:
    payload = {
        "id": record.get("id"),
        "version": record.get("version"),
        "publishedAt": record.get("publishedAt"),
        "changelog": record.get("changelog"),
    }
    return WorkflowVersionSummary.from_dict(payload)


def _version_detail_from_record(record: dict) -> WorkflowVersionDetail:
    payload = {
        "id": record.get("id"),
        "version": record.get("version"),
        "summary": record.get("summary"),
        "description": record.get("description"),
        "tags": record.get("tags"),
        "previewImage": record.get("previewImage"),
        "dependencies": record.get("dependencies"),
        "publishedAt": record.get("publishedAt"),
        "publisherId": record.get("publisherId"),
    }
    return WorkflowVersionDetail.from_dict(payload)


def _visibility_value(value: Visibility | str | None) -> str:
    if value is None:
        return DEFAULT_VISIBILITY
    return value.value if hasattr(value, "value") else str(value)


def _dependencies_payload(dependencies) -> list[dict] | None:
    if not dependencies:
        return None
    payload = []
    for dep in dependencies:
        if hasattr(dep, "to_dict"):
            payload.append(dep.to_dict())
        elif isinstance(dep, dict):
            payload.append(dep)
    return payload or None


def _ensure_valid_version(version: str) -> None:
    try:
        from packaging.version import Version, InvalidVersion  # type: ignore
    except Exception:
        return
    try:
        Version(version)
    except InvalidVersion as exc:
        raise HTTPException(status_code=400, detail="Invalid workflow version.") from exc


def _can_view_workflow(record: dict, actor_id: str | None) -> bool:
    visibility = record.get("visibility") or DEFAULT_VISIBILITY
    if visibility == "public":
        return True
    if is_admin():
        return True
    if not actor_id:
        return False
    if visibility == "internal":
        return True
    return _normalize(record.get("ownerId")) == _normalize(actor_id)


def _require_workflow_access(record: dict | None, actor_id: str | None) -> dict:
    if not record:
        raise HTTPException(status_code=404, detail="Not Found")
    if _can_view_workflow(record, actor_id):
        return record
    raise HTTPException(status_code=404, detail="Not Found")


class WorkflowsService:
    async def list_workflows(
        self,
        q: str | None,
        tag: str | None,
        owner: str | None,
        page: int | None,
        page_size: int | None,
    ) -> WorkflowListResponse:
        query = _normalize(q)
        tag_value = _normalize(tag)
        owner_value = _normalize(owner)
        page_value = page or 1
        size_value = page_size or 20

        actor_id = get_current_actor()
        records = [record for record in list_workflows() if _can_view_workflow(record, actor_id)]
        filtered = [
            record
            for record in records
            if _match_query(record, query)
            and _match_tag(record, tag_value)
            and _match_owner(record, owner_value)
        ]
        fallback_time = datetime.min.replace(tzinfo=timezone.utc)
        filtered.sort(key=lambda item: item.get("updatedAt") or fallback_time, reverse=True)
        page_items, meta = _paginate(filtered, page_value, size_value)
        summaries = [_summary_from_record(record) for record in page_items]
        return WorkflowListResponse(items=summaries, meta=meta)

    async def publish_workflow(
        self,
        workflow_publish_request: WorkflowPublishRequest,
    ) -> WorkflowPublishResponse:
        actor_id = require_actor()
        if workflow_publish_request is None:
            raise HTTPException(status_code=400, detail="Publish payload is required.")
        if not isinstance(workflow_publish_request.definition, dict):
            raise HTTPException(status_code=400, detail="Workflow definition is required.")
        if not workflow_publish_request.name or not workflow_publish_request.name.strip():
            raise HTTPException(status_code=400, detail="Workflow name is required.")
        if not workflow_publish_request.version or not workflow_publish_request.version.strip():
            raise HTTPException(status_code=400, detail="Workflow version is required.")
        _ensure_valid_version(workflow_publish_request.version)
        previous_visibility = None
        if workflow_publish_request.workflow_id:
            existing = get_workflow_record(workflow_publish_request.workflow_id)
            if existing and existing.get("ownerId") != actor_id and not is_admin():
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
            if existing:
                previous_visibility = existing.get("visibility")
        visibility_value = _visibility_value(workflow_publish_request.visibility)
        dependencies = _dependencies_payload(workflow_publish_request.dependencies)
        if dependencies:
            for dep in dependencies:
                name = dep.get("name") if isinstance(dep, dict) else None
                version = dep.get("version") if isinstance(dep, dict) else None
                if not name or not version:
                    raise HTTPException(status_code=400, detail="Dependencies must include name and version.")
                if get_package_version_record(name, version) is None:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Dependency {name}@{version} not found.",
                    )
        try:
            workflow_record, version_record = publish_workflow_version(
                workflow_id=workflow_publish_request.workflow_id,
                name=workflow_publish_request.name,
                version=workflow_publish_request.version,
                summary=workflow_publish_request.summary,
                description=workflow_publish_request.description,
                tags=workflow_publish_request.tags,
                visibility=visibility_value,
                preview_image=workflow_publish_request.preview_image,
                dependencies=dependencies,
                definition=workflow_publish_request.definition,
                publisher_id=actor_id,
            )
        except ValueError as exc:
            if str(exc) == "workflow_version_exists":
                raise HTTPException(status_code=409, detail="Workflow version already exists.") from exc
            raise HTTPException(status_code=400, detail="Unable to publish workflow.") from exc
        record_audit_event(
            action="workflow.publish",
            actor_id=actor_id,
            target_type="workflow",
            target_id=workflow_record.get("id"),
            metadata={
                "version": version_record.get("version"),
                "versionId": version_record.get("id"),
                "name": workflow_record.get("name"),
            },
        )
        if previous_visibility and previous_visibility != visibility_value:
            record_audit_event(
                action="workflow.visibility.update",
                actor_id=actor_id,
                target_type="workflow",
                target_id=workflow_record.get("id"),
                metadata={
                    "from": previous_visibility,
                    "to": visibility_value,
                },
            )
        return WorkflowPublishResponse.from_dict(
            {
                "workflowId": workflow_record.get("id"),
                "versionId": version_record.get("id"),
                "version": version_record.get("version"),
            }
        )

    async def get_workflow(
        self,
        workflowId: str,
    ) -> HubWorkflowDetail:
        record = _require_workflow_access(get_workflow_record(workflowId), get_current_actor())
        return _detail_from_record(record)

    async def list_workflow_versions(
        self,
        workflowId: str,
        page: int | None,
        page_size: int | None,
    ) -> WorkflowVersionList:
        _require_workflow_access(get_workflow_record(workflowId), get_current_actor())
        page_value = page or 1
        size_value = page_size or 20
        try:
            versions = list_workflow_versions(workflowId)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail="Not Found") from exc
        page_items, meta = _paginate(versions, page_value, size_value)
        summaries = [_version_summary_from_record(record) for record in page_items]
        return WorkflowVersionList(items=summaries, meta=meta)

    async def get_workflow_version(
        self,
        workflowId: str,
        versionId: str,
    ) -> WorkflowVersionDetail:
        _require_workflow_access(get_workflow_record(workflowId), get_current_actor())
        record = get_workflow_version_record(workflowId, versionId)
        if record is None:
            raise HTTPException(status_code=404, detail="Not Found")
        return _version_detail_from_record(record)

    async def get_workflow_definition(
        self,
        workflowId: str,
        versionId: str,
    ) -> dict[str, object]:
        _require_workflow_access(get_workflow_record(workflowId), get_current_actor())
        definition = get_workflow_definition(workflowId, versionId)
        if definition is None:
            raise HTTPException(status_code=404, detail="Not Found")
        return definition
