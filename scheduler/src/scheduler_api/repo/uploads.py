"""Chunked upload session storage for local resources."""

from __future__ import annotations

import json
import math
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

from scheduler_api.config.settings import get_api_settings

DEFAULT_CHUNK_SIZE = 8 * 1024 * 1024
MAX_CHUNK_SIZE = 64 * 1024 * 1024
CLEANUP_INTERVAL_SECONDS = 300


class UploadNotFoundError(FileNotFoundError):
    """Raised when an upload session does not exist."""


class UploadConflictError(RuntimeError):
    """Raised when a chunk is uploaded out of order."""

    def __init__(self, expected_part: int) -> None:
        super().__init__(f"Expected part {expected_part}")
        self.expected_part = expected_part


class UploadValidationError(ValueError):
    """Raised when a chunk or session payload is invalid."""


@dataclass
class UploadSession:
    upload_id: str
    filename: str
    size_bytes: int
    provider: Optional[str]
    mime_type: Optional[str]
    sha256: Optional[str]
    chunk_size: int
    uploaded_bytes: int
    next_part: int
    total_parts: int
    status: str
    resource_id: Optional[str]
    metadata: Optional[dict[str, Any]]
    created_at: datetime
    updated_at: datetime
    completed_parts: set[int] = field(default_factory=set)

    def to_dict(self) -> dict[str, Any]:
        return {
            "uploadId": self.upload_id,
            "filename": self.filename,
            "sizeBytes": self.size_bytes,
            "provider": self.provider,
            "mimeType": self.mime_type,
            "sha256": self.sha256,
            "chunkSize": self.chunk_size,
            "uploadedBytes": self.uploaded_bytes,
            "nextPart": self.next_part,
            "totalParts": self.total_parts,
            "status": self.status,
            "resourceId": self.resource_id,
            "metadata": self.metadata,
            "createdAt": self.created_at.isoformat(),
            "updatedAt": self.updated_at.isoformat(),
            "completedParts": sorted(self.completed_parts),
        }

    def to_storage(self) -> dict[str, Any]:
        return {
            "upload_id": self.upload_id,
            "filename": self.filename,
            "size_bytes": self.size_bytes,
            "provider": self.provider,
            "mime_type": self.mime_type,
            "sha256": self.sha256,
            "chunk_size": self.chunk_size,
            "uploaded_bytes": self.uploaded_bytes,
            "next_part": self.next_part,
            "total_parts": self.total_parts,
            "status": self.status,
            "resource_id": self.resource_id,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "completed_parts": sorted(self.completed_parts),
        }

    @classmethod
    def from_storage(cls, payload: dict[str, Any]) -> "UploadSession":
        session = cls(
            upload_id=str(payload["upload_id"]),
            filename=str(payload["filename"]),
            size_bytes=int(payload["size_bytes"]),
            provider=payload.get("provider"),
            mime_type=payload.get("mime_type"),
            sha256=payload.get("sha256"),
            chunk_size=int(payload["chunk_size"]),
            uploaded_bytes=int(payload.get("uploaded_bytes") or 0),
            next_part=int(payload.get("next_part") or 0),
            total_parts=int(payload.get("total_parts") or 0),
            status=str(payload.get("status") or "pending"),
            resource_id=payload.get("resource_id"),
            metadata=payload.get("metadata"),
            created_at=_parse_datetime(payload.get("created_at")) or _utcnow(),
            updated_at=_parse_datetime(payload.get("updated_at")) or _utcnow(),
            completed_parts=_normalize_completed_parts(payload.get("completed_parts")),
        )
        if not session.completed_parts and session.next_part > 0:
            session.completed_parts = set(range(session.next_part))
        if session.completed_parts:
            session.uploaded_bytes = _compute_uploaded_bytes(session)
            session.next_part = _find_next_part(session)
        return session

    def is_complete(self) -> bool:
        return len(self.completed_parts) >= self.total_parts


class UploadSessionStore:
    def __init__(self, base_dir: Path) -> None:
        self._base_dir = base_dir / "_uploads"
        self._base_dir.mkdir(parents=True, exist_ok=True)
        self._last_cleanup: float = 0.0

    def create(
        self,
        *,
        filename: str,
        size_bytes: int,
        provider: Optional[str] = None,
        mime_type: Optional[str],
        sha256: Optional[str],
        chunk_size: Optional[int],
        metadata: Optional[dict[str, Any]],
    ) -> UploadSession:
        self._maybe_cleanup()
        if size_bytes <= 0:
            raise UploadValidationError("sizeBytes must be greater than 0")
        resolved_chunk = _resolve_chunk_size(chunk_size)
        total_parts = max(1, math.ceil(size_bytes / resolved_chunk))
        now = _utcnow()
        upload_id = uuid.uuid4().hex
        session = UploadSession(
            upload_id=upload_id,
            filename=filename,
            size_bytes=size_bytes,
            provider=provider,
            mime_type=mime_type,
            sha256=sha256,
            chunk_size=resolved_chunk,
            uploaded_bytes=0,
            next_part=0,
            total_parts=total_parts,
            status="pending",
            resource_id=None,
            metadata=metadata,
            created_at=now,
            updated_at=now,
            completed_parts=set(),
        )
        self._write_metadata(session)
        self._data_path(upload_id).touch(exist_ok=True)
        return session

    def get(self, upload_id: str) -> UploadSession:
        self._maybe_cleanup()
        payload = self._read_metadata(upload_id)
        return UploadSession.from_storage(payload)

    def mark_aborted(self, upload_id: str) -> UploadSession:
        session = self.get(upload_id)
        session.status = "aborted"
        session.updated_at = _utcnow()
        self._write_metadata(session)
        self._cleanup_files(upload_id)
        return session

    def mark_completed(self, upload_id: str, *, resource_id: str, cleanup_data: bool = False) -> UploadSession:
        session = self.get(upload_id)
        if session.status == "aborted":
            raise UploadValidationError("upload session is aborted")
        session.status = "completed"
        session.resource_id = resource_id
        session.completed_parts = set(range(session.total_parts))
        session.uploaded_bytes = session.size_bytes
        session.next_part = session.total_parts
        session.updated_at = _utcnow()
        self._write_metadata(session)
        if cleanup_data:
            data_path = self._data_path(upload_id)
            if data_path.exists():
                data_path.unlink()
        return session

    def write_part(self, upload_id: str, part_number: int, data: bytes) -> UploadSession:
        session = self.get(upload_id)
        if session.status != "pending":
            raise UploadValidationError("upload session is not active")
        if part_number < 0 or part_number >= session.total_parts:
            raise UploadValidationError("part number out of range")
        expected_size = _expected_part_size(session, part_number)
        if len(data) != expected_size:
            raise UploadValidationError("chunk size mismatch")
        if part_number in session.completed_parts:
            return session
        offset = part_number * session.chunk_size
        self._write_chunk(self._data_path(upload_id), offset, data)
        session.completed_parts.add(part_number)
        session.uploaded_bytes = _compute_uploaded_bytes(session)
        session.next_part = _find_next_part(session)
        session.updated_at = _utcnow()
        self._write_metadata(session)
        return session

    def complete(self, upload_id: str, *, resource_id: str) -> UploadSession:
        session = self.get(upload_id)
        if not session.is_complete():
            raise UploadValidationError("upload is incomplete")
        session.status = "completed"
        session.resource_id = resource_id
        session.updated_at = _utcnow()
        self._write_metadata(session)
        return session

    def data_path(self, upload_id: str) -> Path:
        return self._data_path(upload_id)

    def _data_path(self, upload_id: str) -> Path:
        return self._base_dir / f"{upload_id}.bin"

    def _meta_path(self, upload_id: str) -> Path:
        return self._base_dir / f"{upload_id}.json"

    def _write_metadata(self, session: UploadSession) -> None:
        self._meta_path(session.upload_id).write_text(
            json.dumps(session.to_storage(), ensure_ascii=True, indent=2),
            encoding="utf-8",
        )

    def _read_metadata(self, upload_id: str) -> dict[str, Any]:
        meta_path = self._meta_path(upload_id)
        if not meta_path.is_file():
            raise UploadNotFoundError(upload_id)
        return json.loads(meta_path.read_text(encoding="utf-8"))

    def _cleanup_files(self, upload_id: str) -> None:
        data_path = self._data_path(upload_id)
        meta_path = self._meta_path(upload_id)
        if data_path.exists():
            data_path.unlink()
        if meta_path.exists():
            meta_path.unlink()

    def _maybe_cleanup(self) -> None:
        now = _utcnow().timestamp()
        if now - self._last_cleanup < CLEANUP_INTERVAL_SECONDS:
            return
        settings = get_api_settings()
        ttl_seconds = int(settings.resource_upload_ttl_seconds)
        if ttl_seconds <= 0:
            return
        self._last_cleanup = now
        self._cleanup_expired(ttl_seconds, now)

    def _cleanup_expired(self, ttl_seconds: int, now_timestamp: float) -> None:
        for meta_path in self._base_dir.glob("*.json"):
            try:
                payload = json.loads(meta_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            updated_at = _parse_datetime(payload.get("updated_at")) or _parse_datetime(payload.get("created_at"))
            if not updated_at:
                continue
            age_seconds = now_timestamp - updated_at.timestamp()
            if age_seconds <= ttl_seconds:
                continue
            upload_id = payload.get("upload_id") or meta_path.stem
            if not upload_id:
                continue
            self._cleanup_files(str(upload_id))

    @staticmethod
    def _write_chunk(path: Path, offset: int, data: bytes) -> None:
        mode = "r+b" if path.exists() else "wb"
        with path.open(mode) as handle:
            handle.seek(offset)
            handle.write(data)


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


def _resolve_chunk_size(requested: Optional[int]) -> int:
    if requested is None:
        return DEFAULT_CHUNK_SIZE
    if requested <= 0:
        raise UploadValidationError("chunkSize must be greater than 0")
    return min(int(requested), MAX_CHUNK_SIZE)


def _normalize_completed_parts(value: Any) -> set[int]:
    if not value:
        return set()
    if isinstance(value, (list, tuple, set)):
        parts = []
        for item in value:
            try:
                parts.append(int(item))
            except (TypeError, ValueError):
                continue
        return set(parts)
    return set()


def _expected_part_size(session: UploadSession, part_number: int) -> int:
    if part_number < session.total_parts - 1:
        return session.chunk_size
    remaining = session.size_bytes - session.chunk_size * (session.total_parts - 1)
    return remaining if remaining > 0 else session.chunk_size


def _compute_uploaded_bytes(session: UploadSession) -> int:
    if not session.completed_parts:
        return 0
    uploaded = len(session.completed_parts) * session.chunk_size
    last_part = session.total_parts - 1
    if last_part in session.completed_parts:
        expected_last = _expected_part_size(session, last_part)
        if expected_last < session.chunk_size:
            uploaded -= session.chunk_size - expected_last
    return min(uploaded, session.size_bytes)


def _find_next_part(session: UploadSession) -> int:
    for part in range(session.total_parts):
        if part not in session.completed_parts:
            return part
    return session.total_parts


def _resolve_resource_dir(path: Path) -> Path:
    if path.is_absolute():
        return path
    project_root = Path(__file__).resolve().parents[4]
    return project_root / path


@lru_cache()
def get_upload_store() -> UploadSessionStore:
    settings = get_api_settings()
    base_dir = _resolve_resource_dir(Path(settings.resource_dir))
    return UploadSessionStore(base_dir)


__all__ = [
    "DEFAULT_CHUNK_SIZE",
    "MAX_CHUNK_SIZE",
    "CLEANUP_INTERVAL_SECONDS",
    "UploadNotFoundError",
    "UploadConflictError",
    "UploadValidationError",
    "UploadSession",
    "UploadSessionStore",
    "get_upload_store",
]
