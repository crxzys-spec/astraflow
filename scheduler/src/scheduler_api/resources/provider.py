"""Resource storage providers for scheduler uploads."""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional, Protocol

from fastapi import UploadFile

from scheduler_api.config.settings import get_api_settings


class ResourceNotFoundError(FileNotFoundError):
    """Raised when a resource id does not exist in storage."""


@dataclass
class StoredResource:
    resource_id: str
    provider: str
    type: str
    filename: str
    mime_type: Optional[str]
    size_bytes: int
    sha256: Optional[str]
    created_at: datetime
    expires_at: Optional[datetime] = None
    metadata: Optional[dict[str, Any]] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "resource_id": self.resource_id,
            "provider": self.provider,
            "type": self.type,
            "filename": self.filename,
            "mime_type": self.mime_type,
            "size_bytes": self.size_bytes,
            "sha256": self.sha256,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "metadata": self.metadata or {},
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "StoredResource":
        created_at = payload.get("created_at")
        expires_at = payload.get("expires_at")
        return cls(
            resource_id=payload["resource_id"],
            provider=payload.get("provider", "local"),
            type=payload.get("type", "file"),
            filename=payload.get("filename") or payload.get("resource_id", ""),
            mime_type=payload.get("mime_type"),
            size_bytes=int(payload.get("size_bytes") or 0),
            sha256=payload.get("sha256"),
            created_at=_parse_datetime(created_at) if created_at else _utcnow(),
            expires_at=_parse_datetime(expires_at) if expires_at else None,
            metadata=payload.get("metadata"),
        )


class ResourceProvider(Protocol):
    name: str

    def save_bytes(
        self,
        *,
        filename: str,
        data: bytes,
        content_type: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> StoredResource: ...

    def save_file(
        self,
        *,
        path: Path,
        filename: str,
        content_type: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> StoredResource: ...

    async def save_upload(
        self,
        upload: UploadFile,
        *,
        metadata: Optional[dict[str, Any]] = None,
    ) -> StoredResource: ...

    def get(self, resource_id: str) -> StoredResource: ...

    def open(self, resource_id: str) -> tuple[Path, StoredResource]: ...

    def delete(self, resource_id: str) -> None: ...

    def find_by_sha256(self, sha256: str) -> Optional[StoredResource]: ...


class LocalResourceProvider:
    name = "local"
    _index_filename = "_sha256_index.json"

    def __init__(self, base_dir: Path) -> None:
        self._base_dir = base_dir
        self._base_dir.mkdir(parents=True, exist_ok=True)
        self._index_path = self._base_dir / self._index_filename
        self._sha_index: dict[str, str] = self._load_index()
        self._index_refreshed = False

    async def save_upload(
        self,
        upload: UploadFile,
        *,
        metadata: Optional[dict[str, Any]] = None,
    ) -> StoredResource:
        resource_id = uuid.uuid4().hex
        filename = upload.filename or resource_id
        mime_type = upload.content_type
        target_path = self._resource_path(resource_id)
        sha256, size_bytes = await self._write_upload(upload, target_path)
        stored = self._build_stored(
            resource_id=resource_id,
            filename=filename,
            mime_type=mime_type,
            size_bytes=size_bytes,
            sha256=sha256,
            metadata=metadata,
        )
        self._write_metadata(stored)
        self._record_sha256(stored)
        return stored

    def save_bytes(
        self,
        *,
        filename: str,
        data: bytes,
        content_type: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> StoredResource:
        resource_id = uuid.uuid4().hex
        target_path = self._resource_path(resource_id)
        sha256 = hashlib.sha256(data).hexdigest()
        target_path.write_bytes(data)
        stored = self._build_stored(
            resource_id=resource_id,
            filename=filename,
            mime_type=content_type,
            size_bytes=len(data),
            sha256=sha256,
            metadata=metadata,
        )
        self._write_metadata(stored)
        self._record_sha256(stored)
        return stored

    def save_file(
        self,
        *,
        path: Path,
        filename: str,
        content_type: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> StoredResource:
        if not path.is_file():
            raise FileNotFoundError(str(path))
        resource_id = uuid.uuid4().hex
        target_path = self._resource_path(resource_id)
        sha256, size_bytes = self._hash_file(path)
        path.replace(target_path)
        stored = self._build_stored(
            resource_id=resource_id,
            filename=filename,
            mime_type=content_type,
            size_bytes=size_bytes,
            sha256=sha256,
            metadata=metadata,
        )
        self._write_metadata(stored)
        self._record_sha256(stored)
        return stored

    def get(self, resource_id: str) -> StoredResource:
        stored = self._read_metadata(resource_id)
        if not self._resource_path(resource_id).is_file():
            raise ResourceNotFoundError(resource_id)
        return stored

    def open(self, resource_id: str) -> tuple[Path, StoredResource]:
        stored = self._read_metadata(resource_id)
        file_path = self._resource_path(resource_id)
        if not file_path.is_file():
            raise ResourceNotFoundError(resource_id)
        return file_path, stored

    def delete(self, resource_id: str) -> None:
        file_path = self._resource_path(resource_id)
        meta_path = self._metadata_path(resource_id)
        stored: Optional[StoredResource] = None
        if meta_path.exists():
            try:
                stored = self._read_metadata(resource_id)
            except ResourceNotFoundError:
                stored = None
        if file_path.exists():
            file_path.unlink()
        if meta_path.exists():
            meta_path.unlink()
        if stored and stored.sha256:
            self._remove_sha256(stored.sha256, resource_id)

    def find_by_sha256(self, sha256: str) -> Optional[StoredResource]:
        if not sha256:
            return None
        resource_id = self._sha_index.get(sha256)
        if not resource_id and not self._index_refreshed:
            self._sha_index = self._rebuild_index()
            self._write_index()
            self._index_refreshed = True
            resource_id = self._sha_index.get(sha256)
        if not resource_id:
            return None
        try:
            stored = self.get(resource_id)
        except ResourceNotFoundError:
            self._remove_sha256(sha256, resource_id)
            return None
        if stored.sha256 != sha256:
            self._remove_sha256(sha256, resource_id)
            return None
        return stored

    def _resource_path(self, resource_id: str) -> Path:
        return self._base_dir / resource_id

    def _metadata_path(self, resource_id: str) -> Path:
        return self._base_dir / f"{resource_id}.json"

    def _load_index(self) -> dict[str, str]:
        if self._index_path.is_file():
            try:
                payload = json.loads(self._index_path.read_text(encoding="utf-8"))
                if isinstance(payload, dict):
                    return {str(k): str(v) for k, v in payload.items()}
            except (json.JSONDecodeError, OSError):
                pass
        index = self._rebuild_index()
        self._write_index(index)
        return index

    def _rebuild_index(self) -> dict[str, str]:
        index: dict[str, str] = {}
        for meta_path in self._base_dir.glob("*.json"):
            if meta_path.name == self._index_filename:
                continue
            try:
                payload = json.loads(meta_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            resource_id = payload.get("resource_id")
            sha256 = payload.get("sha256")
            if not resource_id or not sha256:
                continue
            if not self._resource_path(resource_id).is_file():
                continue
            index[str(sha256)] = str(resource_id)
        return index

    def _write_index(self, index: Optional[dict[str, str]] = None) -> None:
        payload = index if index is not None else self._sha_index
        self._index_path.write_text(
            json.dumps(payload, ensure_ascii=True, indent=2),
            encoding="utf-8",
        )

    def _record_sha256(self, stored: StoredResource) -> None:
        if not stored.sha256:
            return
        self._sha_index[stored.sha256] = stored.resource_id
        self._write_index()

    def _remove_sha256(self, sha256: str, resource_id: str) -> None:
        if self._sha_index.get(sha256) != resource_id:
            return
        self._sha_index.pop(sha256, None)
        self._write_index()

    def _read_metadata(self, resource_id: str) -> StoredResource:
        meta_path = self._metadata_path(resource_id)
        if not meta_path.is_file():
            raise ResourceNotFoundError(resource_id)
        payload = json.loads(meta_path.read_text(encoding="utf-8"))
        return StoredResource.from_dict(payload)

    def _write_metadata(self, stored: StoredResource) -> None:
        meta_path = self._metadata_path(stored.resource_id)
        meta_path.write_text(
            json.dumps(stored.to_dict(), ensure_ascii=True, indent=2),
            encoding="utf-8",
        )

    async def _write_upload(self, upload: UploadFile, target: Path) -> tuple[Optional[str], int]:
        hasher = hashlib.sha256()
        size_bytes = 0
        with target.open("wb") as handle:
            while True:
                chunk = await upload.read(1024 * 1024)
                if not chunk:
                    break
                handle.write(chunk)
                size_bytes += len(chunk)
                hasher.update(chunk)
        await upload.close()
        return hasher.hexdigest(), size_bytes

    @staticmethod
    def _hash_file(path: Path) -> tuple[str, int]:
        hasher = hashlib.sha256()
        size_bytes = 0
        with path.open("rb") as handle:
            while True:
                chunk = handle.read(1024 * 1024)
                if not chunk:
                    break
                hasher.update(chunk)
                size_bytes += len(chunk)
        return hasher.hexdigest(), size_bytes

    def _build_stored(
        self,
        *,
        resource_id: str,
        filename: str,
        mime_type: Optional[str],
        size_bytes: int,
        sha256: Optional[str],
        metadata: Optional[dict[str, Any]],
    ) -> StoredResource:
        return StoredResource(
            resource_id=resource_id,
            provider=self.name,
            type="file",
            filename=filename,
            mime_type=mime_type,
            size_bytes=size_bytes,
            sha256=sha256,
            created_at=_utcnow(),
            metadata=metadata or {},
        )


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _parse_datetime(value: Any) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None


def _resolve_resource_dir(path: Path) -> Path:
    if path.is_absolute():
        return path
    project_root = Path(__file__).resolve().parents[4]
    return project_root / path


@lru_cache()
def get_resource_provider() -> ResourceProvider:
    settings = get_api_settings()
    provider = settings.resource_provider.strip().lower()
    if provider != "local":
        raise ValueError(f"Unsupported resource provider: {provider}")
    base_dir = _resolve_resource_dir(Path(settings.resource_dir))
    return LocalResourceProvider(base_dir)
