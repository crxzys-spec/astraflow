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
from scheduler_api.db.models import ResourcePayloadRecord, ResourceRecord
from scheduler_api.infra.resources.records import ResourcePayloadRepository, ResourceRecordRepository


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
    owner_id: Optional[str] = None
    visibility: str = "private"

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
            "owner_id": self.owner_id,
            "visibility": self.visibility,
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
            owner_id=payload.get("owner_id") or payload.get("ownerId"),
            visibility=payload.get("visibility") or "private",
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
        owner_id: Optional[str] = None,
        visibility: Optional[str] = None,
    ) -> StoredResource: ...

    def save_file(
        self,
        *,
        path: Path,
        filename: str,
        content_type: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
        owner_id: Optional[str] = None,
        visibility: Optional[str] = None,
    ) -> StoredResource: ...

    async def save_upload(
        self,
        upload: UploadFile,
        *,
        metadata: Optional[dict[str, Any]] = None,
        owner_id: Optional[str] = None,
        visibility: Optional[str] = None,
    ) -> StoredResource: ...

    def get(self, resource_id: str) -> StoredResource: ...

    def open(self, resource_id: str) -> tuple[Path, StoredResource]: ...

    def list(
        self,
        *,
        owner_id: Optional[str] = None,
        search: Optional[str] = None,
    ) -> list[StoredResource]: ...

    def delete(self, resource_id: str) -> None: ...

    def find_by_sha256(self, sha256: str) -> Optional[StoredResource]: ...


class LocalResourceProvider:
    name = "local"
    _legacy_index_filename = "_sha256_index.json"

    def __init__(self, base_dir: Path) -> None:
        self._base_dir = base_dir
        self._base_dir.mkdir(parents=True, exist_ok=True)
        self._legacy_checked = False
        self._records = ResourceRecordRepository()

    async def save_upload(
        self,
        upload: UploadFile,
        *,
        metadata: Optional[dict[str, Any]] = None,
        owner_id: Optional[str] = None,
        visibility: Optional[str] = None,
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
            owner_id=owner_id,
            visibility=visibility,
        )
        self._upsert_record(stored)
        return stored

    def save_bytes(
        self,
        *,
        filename: str,
        data: bytes,
        content_type: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
        owner_id: Optional[str] = None,
        visibility: Optional[str] = None,
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
            owner_id=owner_id,
            visibility=visibility,
        )
        self._upsert_record(stored)
        return stored

    def save_file(
        self,
        *,
        path: Path,
        filename: str,
        content_type: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
        owner_id: Optional[str] = None,
        visibility: Optional[str] = None,
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
            owner_id=owner_id,
            visibility=visibility,
        )
        self._upsert_record(stored)
        return stored

    def get(self, resource_id: str) -> StoredResource:
        stored = self._get_record(resource_id)
        if stored is None:
            stored = self._read_legacy_metadata(resource_id)
            if stored:
                self._upsert_record(stored)
        if stored is None or not self._resource_path(resource_id).is_file():
            raise ResourceNotFoundError(resource_id)
        return stored

    def open(self, resource_id: str) -> tuple[Path, StoredResource]:
        stored = self.get(resource_id)
        file_path = self._resource_path(resource_id)
        if not file_path.is_file():
            raise ResourceNotFoundError(resource_id)
        return file_path, stored

    def list(
        self,
        *,
        owner_id: Optional[str] = None,
        search: Optional[str] = None,
    ) -> list[StoredResource]:
        if not self._legacy_checked:
            self._load_legacy_records()
        results = self._list_records(owner_id=owner_id, search=search)
        return [item for item in results if self._resource_path(item.resource_id).is_file()]

    def delete(self, resource_id: str) -> None:
        file_path = self._resource_path(resource_id)
        stored: Optional[StoredResource] = self._get_record(resource_id)
        if file_path.exists():
            file_path.unlink()
        self._delete_record(resource_id)
        legacy_path = self._metadata_path(resource_id)
        if legacy_path.exists():
            legacy_path.unlink()

    def find_by_sha256(self, sha256: str) -> Optional[StoredResource]:
        if not sha256:
            return None
        stored = self._find_by_sha256(sha256)
        if stored is None and not self._legacy_checked:
            self._load_legacy_records()
            stored = self._find_by_sha256(sha256)
        if stored and not self._resource_path(stored.resource_id).is_file():
            return None
        return stored

    def _resource_path(self, resource_id: str) -> Path:
        return self._base_dir / resource_id

    def _metadata_path(self, resource_id: str) -> Path:
        return self._base_dir / f"{resource_id}.json"

    def _get_record(self, resource_id: str) -> Optional[StoredResource]:
        record = self._records.get(resource_id)
        if record is None or record.provider != self.name:
            return None
        return _record_to_stored(record)

    def _delete_record(self, resource_id: str) -> None:
        self._records.delete(resource_id)

    def _find_by_sha256(self, sha256: str) -> Optional[StoredResource]:
        record = self._records.find_by_sha256(provider=self.name, sha256=sha256)
        return _record_to_stored(record) if record else None

    def _list_records(
        self,
        *,
        owner_id: Optional[str],
        search: Optional[str],
    ) -> list[StoredResource]:
        records = self._records.list(provider=self.name, owner_id=owner_id, search=search)
        return [_record_to_stored(record) for record in records]

    def _upsert_record(self, stored: StoredResource) -> None:
        record = _stored_to_record(stored)
        self._records.upsert(record)

    def _read_legacy_metadata(self, resource_id: str) -> Optional[StoredResource]:
        meta_path = self._metadata_path(resource_id)
        if not meta_path.is_file():
            return None
        try:
            payload = json.loads(meta_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None
        if not isinstance(payload, dict):
            return None
        try:
            stored = StoredResource.from_dict(payload)
        except (KeyError, TypeError, ValueError):
            return None
        if not self._resource_path(stored.resource_id).is_file():
            return None
        return stored

    def _load_legacy_records(self) -> None:
        self._legacy_checked = True
        legacy_items: list[StoredResource] = []
        for meta_path in self._base_dir.glob("*.json"):
            if meta_path.name == self._legacy_index_filename:
                continue
            try:
                payload = json.loads(meta_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            if not isinstance(payload, dict):
                continue
            try:
                stored = StoredResource.from_dict(payload)
            except (KeyError, TypeError, ValueError):
                continue
            if not self._resource_path(stored.resource_id).is_file():
                continue
            legacy_items.append(stored)
        if not legacy_items:
            return
        existing_ids = self._records.list_ids()
        for stored in legacy_items:
            if stored.resource_id in existing_ids:
                continue
            self._records.upsert(_stored_to_record(stored))

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
        owner_id: Optional[str],
        visibility: Optional[str],
    ) -> StoredResource:
        resolved_meta = metadata or {}
        resolved_owner = owner_id or resolved_meta.get("ownerId") or resolved_meta.get("owner_id")
        resolved_visibility = visibility or resolved_meta.get("visibility") or "private"
        resolved_type = _resolve_resource_type(resolved_meta)
        return StoredResource(
            resource_id=resource_id,
            provider=self.name,
            type=resolved_type,
            filename=filename,
            mime_type=mime_type,
            size_bytes=size_bytes,
            sha256=sha256,
            created_at=_utcnow(),
            metadata=resolved_meta,
            owner_id=resolved_owner,
            visibility=resolved_visibility,
        )


class DbResourceProvider:
    name = "db"

    def __init__(self, base_dir: Path) -> None:
        self._cache_dir = base_dir / "_db_cache"
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._records = ResourceRecordRepository()
        self._payloads = ResourcePayloadRepository()

    async def save_upload(
        self,
        upload: UploadFile,
        *,
        metadata: Optional[dict[str, Any]] = None,
        owner_id: Optional[str] = None,
        visibility: Optional[str] = None,
    ) -> StoredResource:
        resource_id = uuid.uuid4().hex
        filename = upload.filename or resource_id
        mime_type = upload.content_type
        data = await upload.read()
        await upload.close()
        return self._store_bytes(
            resource_id=resource_id,
            filename=filename,
            data=data,
            content_type=mime_type,
            metadata=metadata,
            owner_id=owner_id,
            visibility=visibility,
        )

    def save_bytes(
        self,
        *,
        filename: str,
        data: bytes,
        content_type: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
        owner_id: Optional[str] = None,
        visibility: Optional[str] = None,
    ) -> StoredResource:
        resource_id = uuid.uuid4().hex
        return self._store_bytes(
            resource_id=resource_id,
            filename=filename,
            data=data,
            content_type=content_type,
            metadata=metadata,
            owner_id=owner_id,
            visibility=visibility,
        )

    def save_file(
        self,
        *,
        path: Path,
        filename: str,
        content_type: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
        owner_id: Optional[str] = None,
        visibility: Optional[str] = None,
    ) -> StoredResource:
        if not path.is_file():
            raise FileNotFoundError(str(path))
        data = path.read_bytes()
        stored = self._store_bytes(
            resource_id=uuid.uuid4().hex,
            filename=filename,
            data=data,
            content_type=content_type,
            metadata=metadata,
            owner_id=owner_id,
            visibility=visibility,
        )
        if path.exists():
            path.unlink()
        return stored

    def get(self, resource_id: str) -> StoredResource:
        stored = self._get_record(resource_id)
        if stored is None:
            raise ResourceNotFoundError(resource_id)
        if not self._payload_exists(resource_id):
            raise ResourceNotFoundError(resource_id)
        return stored

    def open(self, resource_id: str) -> tuple[Path, StoredResource]:
        stored = self.get(resource_id)
        payload = self._get_payload(resource_id)
        if payload is None:
            raise ResourceNotFoundError(resource_id)
        cache_path = self._cache_path(resource_id)
        if not cache_path.exists() or cache_path.stat().st_size != stored.size_bytes:
            cache_path.write_bytes(payload)
        return cache_path, stored

    def list(
        self,
        *,
        owner_id: Optional[str] = None,
        search: Optional[str] = None,
    ) -> list[StoredResource]:
        records = self._records.list(
            provider=self.name,
            owner_id=owner_id,
            search=search,
            require_payload=True,
        )
        return [_record_to_stored(record) for record in records]

    def delete(self, resource_id: str) -> None:
        cache_path = self._cache_path(resource_id)
        if cache_path.exists():
            cache_path.unlink()
        self._payloads.delete(resource_id)
        self._records.delete(resource_id)

    def find_by_sha256(self, sha256: str) -> Optional[StoredResource]:
        if not sha256:
            return None
        record = self._records.find_by_sha256(
            provider=self.name,
            sha256=sha256,
            require_payload=True,
        )
        return _record_to_stored(record) if record else None

    def _cache_path(self, resource_id: str) -> Path:
        return self._cache_dir / resource_id

    def _get_record(self, resource_id: str) -> Optional[StoredResource]:
        record = self._records.get(resource_id)
        if record is None or record.provider != self.name:
            return None
        return _record_to_stored(record)

    def _payload_exists(self, resource_id: str) -> bool:
        return self._payloads.exists(resource_id)

    def _get_payload(self, resource_id: str) -> Optional[bytes]:
        return self._payloads.get_bytes(resource_id)

    def _store_bytes(
        self,
        *,
        resource_id: str,
        filename: str,
        data: bytes,
        content_type: Optional[str],
        metadata: Optional[dict[str, Any]],
        owner_id: Optional[str],
        visibility: Optional[str],
    ) -> StoredResource:
        sha256 = hashlib.sha256(data).hexdigest()
        stored = self._build_stored(
            resource_id=resource_id,
            filename=filename,
            mime_type=content_type,
            size_bytes=len(data),
            sha256=sha256,
            metadata=metadata,
            owner_id=owner_id,
            visibility=visibility,
        )
        record = _stored_to_record(stored)
        payload_record = ResourcePayloadRecord(resource_id=resource_id, payload=data)
        self._records.upsert(record)
        self._payloads.upsert(payload_record)
        return stored

    def _build_stored(
        self,
        *,
        resource_id: str,
        filename: str,
        mime_type: Optional[str],
        size_bytes: int,
        sha256: Optional[str],
        metadata: Optional[dict[str, Any]],
        owner_id: Optional[str],
        visibility: Optional[str],
    ) -> StoredResource:
        resolved_meta = metadata or {}
        resolved_owner = owner_id or resolved_meta.get("ownerId") or resolved_meta.get("owner_id")
        resolved_visibility = visibility or resolved_meta.get("visibility") or "private"
        resolved_type = _resolve_resource_type(resolved_meta)
        return StoredResource(
            resource_id=resource_id,
            provider=self.name,
            type=resolved_type,
            filename=filename,
            mime_type=mime_type,
            size_bytes=size_bytes,
            sha256=sha256,
            created_at=_utcnow(),
            metadata=resolved_meta,
            owner_id=resolved_owner,
            visibility=resolved_visibility,
        )

def _resolve_resource_type(metadata: Optional[dict[str, Any]]) -> str:
    if not metadata:
        return "file"
    for key in ("resourceType", "resource_type"):
        value = metadata.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return "file"


def _serialize_metadata(metadata: Optional[dict[str, Any]]) -> Optional[str]:
    if metadata is None:
        return None
    try:
        return json.dumps(metadata, ensure_ascii=True)
    except (TypeError, ValueError):
        return json.dumps({}, ensure_ascii=True)


def _parse_metadata(value: Optional[str]) -> Optional[dict[str, Any]]:
    if not value:
        return None
    try:
        payload = json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return None
    if isinstance(payload, dict):
        return payload
    return None


def _record_to_stored(record: ResourceRecord) -> StoredResource:
    return StoredResource(
        resource_id=record.resource_id,
        provider=record.provider,
        type=record.resource_type,
        filename=record.filename,
        mime_type=record.mime_type,
        size_bytes=int(record.size_bytes),
        sha256=record.sha256,
        created_at=record.created_at,
        expires_at=record.expires_at,
        metadata=_parse_metadata(record.metadata_json),
        owner_id=record.owner_id,
        visibility=record.visibility or "private",
    )


def _stored_to_record(stored: StoredResource) -> ResourceRecord:
    return ResourceRecord(
        resource_id=stored.resource_id,
        provider=stored.provider or "local",
        resource_type=stored.type or "file",
        filename=stored.filename,
        owner_id=stored.owner_id,
        visibility=stored.visibility,
        mime_type=stored.mime_type,
        size_bytes=stored.size_bytes,
        sha256=stored.sha256,
        created_at=stored.created_at,
        expires_at=stored.expires_at,
        metadata_json=_serialize_metadata(stored.metadata),
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
    project_root = Path(__file__).resolve().parents[5]
    return project_root / path


@lru_cache()
def get_resource_provider_registry() -> dict[str, ResourceProvider]:
    settings = get_api_settings()
    base_dir = _resolve_resource_dir(Path(settings.resource_dir))
    available: dict[str, ResourceProvider] = {
        "local": LocalResourceProvider(base_dir),
        "db": DbResourceProvider(base_dir),
    }
    normalized = _normalize_providers(settings.resource_providers, settings.resource_provider)
    registry: dict[str, ResourceProvider] = {}
    for name in normalized:
        provider = available.get(name)
        if provider is None:
            raise ValueError(f"Unsupported resource provider: {name}")
        registry[name] = provider
    return registry


def get_resource_provider(name: Optional[str] = None) -> ResourceProvider:
    settings = get_api_settings()
    default_name = _normalize_provider_name(settings.resource_provider)
    provider_name = _normalize_provider_name(name) if name else default_name
    registry = get_resource_provider_registry()
    provider = registry.get(provider_name)
    if provider is None:
        raise ValueError(f"Unsupported resource provider: {provider_name}")
    return provider


def get_resource_provider_for(resource_id: str) -> ResourceProvider:
    record = ResourceRecordRepository().get(resource_id)
    if record is None:
        fallback = get_resource_provider()
        try:
            fallback.get(resource_id)
        except ResourceNotFoundError as exc:
            raise exc
        return fallback
    return get_resource_provider(record.provider)


def list_resource_providers() -> list[str]:
    return list(get_resource_provider_registry().keys())


def _normalize_provider_name(value: Optional[str]) -> str:
    if not value:
        return "local"
    name = str(value).strip().lower()
    return name or "local"


def _normalize_providers(values: Optional[list[str]], default_name: Optional[str]) -> list[str]:
    normalized = [
        _normalize_provider_name(item)
        for item in (values or [])
        if item is not None and str(item).strip()
    ]
    default_value = _normalize_provider_name(default_name)
    if default_value not in normalized:
        normalized.insert(0, default_value)
    seen: set[str] = set()
    deduped: list[str] = []
    for item in normalized:
        if item in seen:
            continue
        seen.add(item)
        deduped.append(item)
    return deduped
