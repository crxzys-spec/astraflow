"""Service layer for resource operations."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import UploadFile

from scheduler_api.models.resource_upload_init_request import ResourceUploadInitRequest
from scheduler_api.infra.resources import (
    ResourceNotFoundError,
    StoredResource,
    get_resource_provider,
    get_resource_provider_for,
    list_resource_providers,
)
from scheduler_api.repo.uploads import (
    UploadConflictError,
    UploadNotFoundError,
    UploadSession,
    UploadValidationError,
    get_upload_store,
)


class ResourceService:
    def list_resources(
        self,
        *,
        owner_id: Optional[str],
        search: Optional[str],
    ) -> list[StoredResource]:
        resources: list[StoredResource] = []
        for provider_name in list_resource_providers():
            provider = get_resource_provider(provider_name)
            resources.extend(provider.list(owner_id=owner_id, search=search))
        resources.sort(key=lambda item: item.created_at, reverse=True)
        return resources

    async def upload_resource(
        self,
        *,
        file: UploadFile,
        provider: Optional[str],
        owner_id: Optional[str],
        visibility: str,
    ) -> StoredResource:
        resolved_provider = self._resolve_provider(provider)
        stored = await resolved_provider.save_upload(file, owner_id=owner_id, visibility=visibility)
        return stored

    def create_upload_session(
        self,
        *,
        request: ResourceUploadInitRequest,
        owner_id: Optional[str],
    ) -> UploadSession:
        if request is None:
            raise ValueError("Missing upload payload.")
        payload = request.model_dump(by_alias=True, exclude_none=True)
        filename = self._sanitize_filename(payload.get("filename")) or ""
        if not filename:
            raise ValueError("filename is required.")
        size_bytes = payload.get("sizeBytes")
        if size_bytes is None:
            raise ValueError("sizeBytes is required.")
        try:
            size_value = int(size_bytes)
        except (TypeError, ValueError) as exc:
            raise ValueError("sizeBytes must be an integer.") from exc
        provider_name = payload.get("provider")
        resolved_provider = self._resolve_provider(provider_name)
        sha256 = payload.get("sha256")
        if sha256 is not None:
            sha256 = str(sha256).strip().lower() or None
        metadata = payload.get("metadata") or {}
        if owner_id and "ownerId" not in metadata and "owner_id" not in metadata:
            metadata["ownerId"] = owner_id
        if "visibility" not in metadata:
            metadata["visibility"] = "private"
        store = get_upload_store()
        if sha256:
            stored = resolved_provider.find_by_sha256(sha256)
            if stored and stored.size_bytes == size_value:
                session = store.create(
                    filename=filename,
                    size_bytes=size_value,
                    provider=resolved_provider.name,
                    mime_type=payload.get("mimeType"),
                    sha256=sha256,
                    chunk_size=payload.get("chunkSize"),
                    metadata=metadata,
                )
                return store.mark_completed(
                    session.upload_id,
                    resource_id=stored.resource_id,
                    cleanup_data=True,
                )
        return store.create(
            filename=filename,
            size_bytes=size_value,
            provider=resolved_provider.name,
            mime_type=payload.get("mimeType"),
            sha256=sha256,
            chunk_size=payload.get("chunkSize"),
            metadata=metadata,
        )

    def get_upload_session(self, upload_id: str) -> UploadSession:
        store = get_upload_store()
        return store.get(upload_id)

    def abort_upload_session(self, upload_id: str) -> None:
        store = get_upload_store()
        store.mark_aborted(upload_id)

    async def write_upload_part(
        self,
        *,
        upload_id: str,
        part_number: int,
        file: UploadFile,
    ) -> tuple[UploadSession, int]:
        if file is None:
            raise ValueError("Missing upload payload.")
        data = await file.read()
        await file.close()
        store = get_upload_store()
        session = store.write_part(upload_id, part_number, data)
        return session, len(data)

    def complete_upload(self, upload_id: str) -> StoredResource:
        store = get_upload_store()
        session = store.get(upload_id)
        if session.status == "aborted":
            raise UploadValidationError("Upload session is aborted.")
        if session.status == "completed":
            if session.resource_id:
                stored = get_resource_provider_for(session.resource_id).get(session.resource_id)
                return stored
            raise UploadValidationError("Upload session already completed.")
        if session.uploaded_bytes < session.size_bytes:
            raise UploadValidationError("Upload is incomplete.")
        resolved_provider = self._resolve_provider(session.provider)
        temp_path = store.data_path(upload_id)
        owner_id = None
        visibility = None
        if session.metadata:
            owner_id = session.metadata.get("ownerId") or session.metadata.get("owner_id")
            visibility = session.metadata.get("visibility")
        stored = resolved_provider.save_file(
            path=temp_path,
            filename=session.filename,
            content_type=session.mime_type,
            metadata=session.metadata,
            owner_id=owner_id,
            visibility=visibility,
        )
        if session.sha256 and stored.sha256 and session.sha256 != stored.sha256:
            resolved_provider.delete(stored.resource_id)
            raise UploadValidationError("SHA256 mismatch.")
        store.complete(upload_id, resource_id=stored.resource_id)
        return stored

    def get_resource(self, resource_id: str) -> StoredResource:
        provider = get_resource_provider_for(resource_id)
        return provider.get(resource_id)

    def delete_resource(self, resource_id: str) -> None:
        provider = get_resource_provider_for(resource_id)
        provider.get(resource_id)
        provider.delete(resource_id)

    def open_resource(self, resource_id: str) -> tuple[Path, StoredResource]:
        provider = get_resource_provider_for(resource_id)
        return provider.open(resource_id)

    @staticmethod
    def _sanitize_filename(raw: Optional[str]) -> str:
        if not raw:
            return ""
        try:
            return Path(raw).name
        except Exception:
            return str(raw)

    @staticmethod
    def _resolve_provider(provider: Optional[str]):
        return get_resource_provider(provider)


__all__ = [
    "ResourceService",
    "ResourceNotFoundError",
    "UploadConflictError",
    "UploadNotFoundError",
    "UploadValidationError",
]
