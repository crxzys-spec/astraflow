from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from fastapi import HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import StrictStr

from scheduler_api.apis.resources_api_base import BaseResourcesApi
from scheduler_api.auth.context import get_current_token
from scheduler_api.auth.roles import WORKFLOW_EDIT_ROLES, WORKFLOW_VIEW_ROLES, require_roles
from scheduler_api.models.resource_grant import ResourceGrant
from scheduler_api.models.resource_grant_create_request import ResourceGrantCreateRequest
from scheduler_api.models.resource_grant_list import ResourceGrantList
from scheduler_api.models.resource_grant_scope import ResourceGrantScope
from scheduler_api.models.resource import Resource
from scheduler_api.models.resource_list import ResourceList
from scheduler_api.models.resource_upload_init_request import ResourceUploadInitRequest
from scheduler_api.models.resource_upload_part import ResourceUploadPart
from scheduler_api.models.resource_upload_session import ResourceUploadSession
from scheduler_api.resources import (
    ResourceGrantNotFoundError,
    ResourceNotFoundError,
    StoredResource,
    StoredResourceGrant,
    get_resource_grant_store,
    get_resource_provider,
    get_resource_provider_for,
    list_resource_providers,
)
from scheduler_api.resources.uploads import (
    UploadConflictError,
    UploadNotFoundError,
    UploadValidationError,
    get_upload_store,
)


class ResourcesApiImpl(BaseResourcesApi):
    async def list_resources(
        self,
        limit: Optional[int],
        cursor: Optional[str],
        search: Optional[StrictStr],
        owner_id: Optional[StrictStr],
    ) -> ResourceList:
        del cursor  # cursor reserved for future pagination
        token = require_roles(*WORKFLOW_VIEW_ROLES)
        is_admin = "admin" in (token.roles if token else [])
        owner_filter = str(owner_id) if owner_id else None
        if owner_filter == "me" or not owner_filter:
            owner_filter = token.sub if token else None
        elif not is_admin and token and owner_filter != token.sub:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient role to view other users' resources.",
            )
        resources = []
        for provider_name in list_resource_providers():
            provider = get_resource_provider(provider_name)
            resources.extend(provider.list(owner_id=owner_filter, search=str(search) if search else None))
        resources.sort(key=lambda item: item.created_at, reverse=True)
        if limit:
            resources = resources[: max(0, int(limit))]
        return ResourceList(
            items=[_to_resource_model(item) for item in resources],
            next_cursor=None,
        )

    async def upload_resource(
        self,
        file: UploadFile,
        provider: Optional[StrictStr],
    ) -> Resource:
        require_roles(*WORKFLOW_EDIT_ROLES)
        token = get_current_token()
        owner_id = token.sub if token else None
        visibility = "private"
        if file is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing upload payload.")
        resolved_provider = _resolve_provider(provider)
        stored = await resolved_provider.save_upload(file, owner_id=owner_id, visibility=visibility)
        return _to_resource_model(stored)

    async def create_resource_upload(
        self,
        resource_upload_init_request: ResourceUploadInitRequest,
    ) -> ResourceUploadSession:
        require_roles(*WORKFLOW_EDIT_ROLES)
        token = get_current_token()
        if resource_upload_init_request is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing upload payload.")
        payload = resource_upload_init_request.model_dump(by_alias=True, exclude_none=True)
        filename = _sanitize_filename(payload.get("filename")) or ""
        if not filename:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="filename is required.")
        size_bytes = payload.get("sizeBytes")
        if size_bytes is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="sizeBytes is required.")
        try:
            size_value = int(size_bytes)
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="sizeBytes must be an integer.") from exc
        provider_name = payload.get("provider")
        resolved_provider = _resolve_provider(provider_name)
        sha256 = payload.get("sha256")
        if sha256 is not None:
            sha256 = str(sha256).strip().lower() or None
        metadata = payload.get("metadata") or {}
        if token and token.sub and "ownerId" not in metadata and "owner_id" not in metadata:
            metadata["ownerId"] = token.sub
        if "visibility" not in metadata:
            metadata["visibility"] = "private"
        store = get_upload_store()
        if sha256:
            stored = resolved_provider.find_by_sha256(sha256)
            if stored and stored.size_bytes == size_value:
                try:
                    session = store.create(
                        filename=filename,
                        size_bytes=size_value,
                        provider=resolved_provider.name,
                        mime_type=payload.get("mimeType"),
                        sha256=sha256,
                        chunk_size=payload.get("chunkSize"),
                        metadata=metadata,
                    )
                    session = store.mark_completed(session.upload_id, resource_id=stored.resource_id, cleanup_data=True)
                except UploadValidationError as exc:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
                return ResourceUploadSession.from_dict(session.to_dict())
        try:
            session = store.create(
                filename=filename,
                size_bytes=size_value,
                provider=resolved_provider.name,
                mime_type=payload.get("mimeType"),
                sha256=sha256,
                chunk_size=payload.get("chunkSize"),
                metadata=metadata,
            )
        except UploadValidationError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        return ResourceUploadSession.from_dict(session.to_dict())

    async def get_resource_upload(self, uploadId: StrictStr) -> ResourceUploadSession:
        require_roles(*WORKFLOW_VIEW_ROLES)
        store = get_upload_store()
        try:
            session = store.get(uploadId)
        except UploadNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        return ResourceUploadSession.from_dict(session.to_dict())

    async def delete_resource_upload(self, uploadId: StrictStr) -> None:
        require_roles(*WORKFLOW_EDIT_ROLES)
        store = get_upload_store()
        try:
            store.mark_aborted(uploadId)
        except UploadNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        return None

    async def upload_resource_part(
        self,
        uploadId: StrictStr,
        partNumber: int,
        file: UploadFile,
    ) -> ResourceUploadPart:
        require_roles(*WORKFLOW_EDIT_ROLES)
        if file is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing upload payload.")
        data = await file.read()
        await file.close()
        store = get_upload_store()
        try:
            session = store.write_part(uploadId, partNumber, data)
        except UploadNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except UploadConflictError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Expected part {exc.expected_part}.",
            ) from exc
        except UploadValidationError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        status_value = "completed" if session.uploaded_bytes >= session.size_bytes else "pending"
        return ResourceUploadPart.from_dict(
            {
                "uploadId": session.upload_id,
                "partNumber": partNumber,
                "receivedBytes": len(data),
                "uploadedBytes": session.uploaded_bytes,
                "nextPart": session.next_part,
                "status": status_value,
            }
        )

    async def complete_resource_upload(self, uploadId: StrictStr) -> Resource:
        require_roles(*WORKFLOW_EDIT_ROLES)
        store = get_upload_store()
        try:
            session = store.get(uploadId)
        except UploadNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        if session.status == "aborted":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Upload session is aborted.")
        if session.status == "completed":
            if session.resource_id:
                try:
                    stored = get_resource_provider_for(session.resource_id).get(session.resource_id)
                except ResourceNotFoundError as exc:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
                return _to_resource_model(stored)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Upload session already completed.")
        if session.uploaded_bytes < session.size_bytes:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Upload is incomplete.")
        resolved_provider = _resolve_provider(session.provider)
        temp_path = store.data_path(uploadId)
        owner_id = None
        visibility = None
        if session.metadata:
            owner_id = session.metadata.get("ownerId") or session.metadata.get("owner_id")
            visibility = session.metadata.get("visibility")
        try:
            stored = resolved_provider.save_file(
                path=temp_path,
                filename=session.filename,
                content_type=session.mime_type,
                metadata=session.metadata,
                owner_id=owner_id,
                visibility=visibility,
            )
        except FileNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        if session.sha256 and stored.sha256 and session.sha256 != stored.sha256:
            resolved_provider.delete(stored.resource_id)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="SHA256 mismatch.")
        store.complete(uploadId, resource_id=stored.resource_id)
        return _to_resource_model(stored)

    async def get_resource(self, resourceId: StrictStr) -> Resource:
        require_roles(*WORKFLOW_VIEW_ROLES)
        try:
            stored = get_resource_provider_for(resourceId).get(resourceId)
        except ResourceNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        return _to_resource_model(stored)

    async def delete_resource(self, resourceId: StrictStr) -> None:
        require_roles(*WORKFLOW_EDIT_ROLES)
        try:
            provider = get_resource_provider_for(resourceId)
            provider.get(resourceId)
        except ResourceNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        provider.delete(resourceId)
        return None

    async def download_resource(self, resourceId: StrictStr) -> FileResponse:
        require_roles(*WORKFLOW_VIEW_ROLES)
        try:
            file_path, stored = get_resource_provider_for(resourceId).open(resourceId)
        except ResourceNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        media_type = stored.mime_type or "application/octet-stream"
        return FileResponse(
            path=file_path,
            media_type=media_type,
            filename=stored.filename or file_path.name,
        )

    async def list_resource_grants(
        self,
        workflow_id: Optional[StrictStr],
        package_name: Optional[StrictStr],
        package_version: Optional[StrictStr],
        resource_key: Optional[StrictStr],
        scope: Optional[ResourceGrantScope],
        resource_id: Optional[StrictStr],
    ) -> ResourceGrantList:
        token = require_roles(*WORKFLOW_VIEW_ROLES)
        is_admin = "admin" in (token.roles if token else [])
        store = get_resource_grant_store()
        scope_value = _enum_value(scope)
        grants = store.list(
            created_by=None if is_admin else token.sub,
            workflow_id=str(workflow_id) if workflow_id else None,
            package_name=str(package_name) if package_name else None,
            package_version=str(package_version) if package_version else None,
            resource_key=str(resource_key) if resource_key else None,
            resource_id=str(resource_id) if resource_id else None,
            scope=scope_value,
        )
        return ResourceGrantList(items=[_to_resource_grant_model(grant) for grant in grants])

    async def create_resource_grant(
        self,
        resource_grant_create_request: ResourceGrantCreateRequest,
    ) -> ResourceGrant:
        token = require_roles(*WORKFLOW_EDIT_ROLES)
        if resource_grant_create_request is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing grant payload.")
        payload = resource_grant_create_request.model_dump(by_alias=True, exclude_none=True)
        resource_id = payload.get("resourceId") or resource_grant_create_request.resource_id
        package_name = payload.get("packageName") or resource_grant_create_request.package_name
        resource_key = payload.get("resourceKey") or resource_grant_create_request.resource_key
        scope_value = _enum_value(payload.get("scope") or resource_grant_create_request.scope)
        workflow_id = payload.get("workflowId") or resource_grant_create_request.workflow_id
        package_version = payload.get("packageVersion") or resource_grant_create_request.package_version
        actions = payload.get("actions") or resource_grant_create_request.actions or []
        metadata = payload.get("metadata") or resource_grant_create_request.metadata

        if not resource_id or not package_name or not resource_key:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing required grant fields.")
        if not scope_value:
            scope_value = "workflow"
        if scope_value == "workflow" and not workflow_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="workflowId is required for workflow-scoped grants.",
            )
        action_values = [_enum_value(action) for action in actions if action is not None]
        if not action_values:
            action_values = ["read"]

        try:
            stored = get_resource_provider_for(str(resource_id)).get(str(resource_id))
        except ResourceNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        is_admin = "admin" in (token.roles if token else [])
        if stored.owner_id and not is_admin and stored.owner_id != token.sub:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the resource owner can grant access.",
            )

        store = get_resource_grant_store()
        grant = store.create(
            resource_id=str(resource_id),
            package_name=str(package_name),
            resource_key=str(resource_key),
            scope=str(scope_value),
            actions=[str(action) for action in action_values],
            package_version=str(package_version) if package_version else None,
            workflow_id=str(workflow_id) if workflow_id else None,
            created_by=token.sub if token else None,
            metadata=metadata if isinstance(metadata, dict) else None,
        )
        return _to_resource_grant_model(grant)

    async def get_resource_grant(self, grantId: StrictStr) -> ResourceGrant:
        token = require_roles(*WORKFLOW_VIEW_ROLES)
        is_admin = "admin" in (token.roles if token else [])
        store = get_resource_grant_store()
        try:
            grant = store.get(str(grantId))
        except ResourceGrantNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        if not is_admin and grant.created_by != token.sub:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
        return _to_resource_grant_model(grant)

    async def delete_resource_grant(self, grantId: StrictStr) -> None:
        token = require_roles(*WORKFLOW_EDIT_ROLES)
        is_admin = "admin" in (token.roles if token else [])
        store = get_resource_grant_store()
        try:
            grant = store.get(str(grantId))
        except ResourceGrantNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        if not is_admin and grant.created_by != token.sub:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
        store.delete(str(grantId))
        return None


def _sanitize_filename(raw: Optional[str]) -> str:
    if not raw:
        return ""
    try:
        return Path(raw).name
    except Exception:
        return str(raw)


def _to_resource_model(stored: StoredResource) -> Resource:
    return Resource(
        resource_id=stored.resource_id,
        provider=stored.provider,
        type=stored.type,
        filename=stored.filename,
        owner_id=stored.owner_id,
        visibility=stored.visibility,
        mime_type=stored.mime_type,
        size_bytes=stored.size_bytes,
        sha256=stored.sha256,
        created_at=stored.created_at,
        expires_at=stored.expires_at,
        metadata=stored.metadata,
        download_url=f"/api/v1/resources/{stored.resource_id}/download",
    )


def _to_resource_grant_model(grant: StoredResourceGrant) -> ResourceGrant:
    return ResourceGrant(
        grant_id=grant.grant_id,
        resource_id=grant.resource_id,
        package_name=grant.package_name,
        package_version=grant.package_version,
        resource_key=grant.resource_key,
        scope=grant.scope,
        workflow_id=grant.workflow_id,
        actions=grant.actions,
        created_at=grant.created_at,
        created_by=grant.created_by,
        metadata=grant.metadata,
    )


def _enum_value(value: Any) -> Optional[str]:
    if value is None:
        return None
    return value.value if hasattr(value, "value") else str(value)


def _resolve_provider(provider: Optional[str]) -> Any:
    try:
        return get_resource_provider(provider)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
