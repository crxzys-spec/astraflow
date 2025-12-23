from __future__ import annotations

import mimetypes
from pathlib import Path
from typing import Optional, Tuple, Union

from fastapi import HTTPException, UploadFile, status
from starlette.datastructures import UploadFile as StarletteUploadFile
from fastapi.responses import FileResponse
from pydantic import StrictBytes, StrictStr

from scheduler_api.apis.resources_api_base import BaseResourcesApi
from scheduler_api.auth.roles import WORKFLOW_EDIT_ROLES, WORKFLOW_VIEW_ROLES, require_roles
from scheduler_api.models.resource import Resource
from scheduler_api.models.resource_upload_init_request import ResourceUploadInitRequest
from scheduler_api.models.resource_upload_part import ResourceUploadPart
from scheduler_api.models.resource_upload_session import ResourceUploadSession
from scheduler_api.resources import ResourceNotFoundError, StoredResource, get_resource_provider
from scheduler_api.resources.uploads import (
    UploadConflictError,
    UploadNotFoundError,
    UploadValidationError,
    get_upload_store,
)

UploadParam = Union[StrictBytes, StrictStr, Tuple[StrictStr, StrictBytes], UploadFile, StarletteUploadFile]


class ResourcesApiImpl(BaseResourcesApi):
    async def upload_resource(self, file: UploadParam) -> Resource:
        require_roles(*WORKFLOW_EDIT_ROLES)
        if isinstance(file, StarletteUploadFile):
            provider = get_resource_provider()
            stored = await provider.save_upload(file)
            return _to_resource_model(stored)
        filename, payload = _normalize_upload(file)
        if payload is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing upload payload.",
            )
        content_type = mimetypes.guess_type(filename)[0]
        provider = get_resource_provider()
        stored = provider.save_bytes(
            filename=filename,
            data=payload,
            content_type=content_type,
        )
        return _to_resource_model(stored)

    async def create_resource_upload(
        self,
        resource_upload_init_request: ResourceUploadInitRequest,
    ) -> ResourceUploadSession:
        require_roles(*WORKFLOW_EDIT_ROLES)
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
        sha256 = payload.get("sha256")
        if sha256 is not None:
            sha256 = str(sha256).strip().lower() or None
        store = get_upload_store()
        if sha256:
            provider = get_resource_provider()
            stored = provider.find_by_sha256(sha256)
            if stored and stored.size_bytes == size_value:
                try:
                    session = store.create(
                        filename=filename,
                        size_bytes=size_value,
                        mime_type=payload.get("mimeType"),
                        sha256=sha256,
                        chunk_size=payload.get("chunkSize"),
                        metadata=payload.get("metadata"),
                    )
                    session = store.mark_completed(session.upload_id, resource_id=stored.resource_id, cleanup_data=True)
                except UploadValidationError as exc:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
                return ResourceUploadSession.from_dict(session.to_dict())
        try:
            session = store.create(
                filename=filename,
                size_bytes=size_value,
                mime_type=payload.get("mimeType"),
                sha256=sha256,
                chunk_size=payload.get("chunkSize"),
                metadata=payload.get("metadata"),
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
                provider = get_resource_provider()
                try:
                    stored = provider.get(session.resource_id)
                except ResourceNotFoundError as exc:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
                return _to_resource_model(stored)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Upload session already completed.")
        if session.uploaded_bytes < session.size_bytes:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Upload is incomplete.")
        provider = get_resource_provider()
        temp_path = store.data_path(uploadId)
        try:
            stored = provider.save_file(
                path=temp_path,
                filename=session.filename,
                content_type=session.mime_type,
                metadata=session.metadata,
            )
        except FileNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        if session.sha256 and stored.sha256 and session.sha256 != stored.sha256:
            provider.delete(stored.resource_id)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="SHA256 mismatch.")
        store.complete(uploadId, resource_id=stored.resource_id)
        return _to_resource_model(stored)

    async def get_resource(self, resourceId: StrictStr) -> Resource:
        require_roles(*WORKFLOW_VIEW_ROLES)
        provider = get_resource_provider()
        try:
            stored = provider.get(resourceId)
        except ResourceNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        return _to_resource_model(stored)

    async def delete_resource(self, resourceId: StrictStr) -> None:
        require_roles(*WORKFLOW_EDIT_ROLES)
        provider = get_resource_provider()
        try:
            provider.get(resourceId)
        except ResourceNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        provider.delete(resourceId)
        return None

    async def download_resource(self, resourceId: StrictStr) -> FileResponse:
        require_roles(*WORKFLOW_VIEW_ROLES)
        provider = get_resource_provider()
        try:
            file_path, stored = provider.open(resourceId)
        except ResourceNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        media_type = stored.mime_type or "application/octet-stream"
        return FileResponse(
            path=file_path,
            media_type=media_type,
            filename=stored.filename or file_path.name,
        )


def _normalize_upload(file: UploadParam) -> Tuple[str, Optional[bytes]]:
    if file is None:
        return "upload.bin", None
    if isinstance(file, tuple):
        name, content = file
        filename = _sanitize_filename(name) or "upload.bin"
        return filename, content
    if isinstance(file, bytes):
        return "upload.bin", file
    if isinstance(file, str):
        return "upload.txt", file.encode("utf-8")
    return "upload.bin", None


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
        mime_type=stored.mime_type,
        size_bytes=stored.size_bytes,
        sha256=stored.sha256,
        created_at=stored.created_at,
        expires_at=stored.expires_at,
        metadata=stored.metadata,
        download_url=f"/api/v1/resources/{stored.resource_id}/download",
    )
