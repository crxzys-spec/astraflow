"""Simple resource registry for worker-side artifacts and sessions."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class ResourceHandle:
    """Metadata describing a stored resource."""

    resource_id: str
    type: str
    scope: Optional[str] = None
    path: Optional[Path] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    size_bytes: Optional[int] = None
    created_at: datetime = field(default_factory=_utcnow)
    expires_at: Optional[datetime] = None
    in_use: int = 0
    state: str = "active"

    def is_expired(self, now: Optional[datetime] = None) -> bool:
        if self.expires_at is None:
            return False
        return (now or _utcnow()) >= self.expires_at


class ResourceRegistry:
    """Tracks reusable resources (files, sessions, models) for worker packages."""

    def __init__(self, *, worker_id: str, base_dir: Optional[Path] = None) -> None:
        self._worker_id = worker_id
        self._base_dir = base_dir
        self._handles: Dict[str, ResourceHandle] = {}
        self._scope_index: Dict[str, set[str]] = {}
        self._lock = threading.RLock()

    @property
    def worker_id(self) -> str:
        return self._worker_id

    @property
    def base_dir(self) -> Optional[Path]:
        return self._base_dir

    def register(
        self,
        *,
        resource_id: str,
        resource_type: str,
        scope: Optional[str] = None,
        path: Optional[Path] = None,
        metadata: Optional[Dict[str, Any]] = None,
        size_bytes: Optional[int] = None,
        expires_at: Optional[datetime] = None,
    ) -> ResourceHandle:
        """Register a new resource entry or replace metadata."""

        handle = ResourceHandle(
            resource_id=resource_id,
            type=resource_type,
            scope=scope,
            path=path,
            metadata=metadata or {},
            size_bytes=size_bytes,
            expires_at=expires_at,
        )
        with self._lock:
            self._handles[resource_id] = handle
            if scope:
                self._scope_index.setdefault(scope, set()).add(resource_id)
        return handle

    def register_file(
        self,
        *,
        resource_id: str,
        file_path: Path,
        scope: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        expires_at: Optional[datetime] = None,
    ) -> ResourceHandle:
        """Register a file on disk and capture its size and path metadata."""

        file_path = file_path.resolve()
        try:
            stat = file_path.stat()
            size_bytes = stat.st_size
        except FileNotFoundError as exc:
            raise FileNotFoundError(f"Resource file {file_path} not found") from exc
        meta = dict(metadata or {})
        meta.setdefault("path", str(file_path))
        if self._base_dir:
            try:
                relative = file_path.relative_to(self._base_dir.resolve())
                meta.setdefault("relative_path", str(relative))
            except ValueError:
                pass
        return self.register(
            resource_id=resource_id,
            resource_type="file",
            scope=scope,
            path=file_path,
            metadata=meta,
            size_bytes=size_bytes,
            expires_at=expires_at,
        )

    def lease(self, resource_id: str) -> ResourceHandle:
        """Mark the resource as in-use and return metadata."""

        with self._lock:
            handle = self._handles.get(resource_id)
            if not handle:
                raise KeyError(f"resource {resource_id} not found")
            handle.in_use += 1
            return handle

    def release(self, resource_id: str, *, reason: Optional[str] = None) -> None:
        """Release a lease; once all leases are released the resource becomes idle."""

        with self._lock:
            handle = self._handles.get(resource_id)
            if not handle:
                return
            handle.in_use = max(handle.in_use - 1, 0)
            if reason and reason == "evicted":
                handle.state = "evicted"

    def touch(self, resource_id: str, *, expires_at: Optional[datetime] = None) -> None:
        """Extend the lifetime of a resource."""

        with self._lock:
            handle = self._handles.get(resource_id)
            if not handle:
                return
            handle.expires_at = expires_at

    def release_scope(self, scope: str) -> None:
        """Release (and delete) all resources belonging to the given scope."""

        with self._lock:
            resource_ids = self._scope_index.pop(scope, set())
            for resource_id in resource_ids:
                self._handles.pop(resource_id, None)

    def list(self, *, scope: Optional[str] = None, resource_type: Optional[str] = None) -> List[ResourceHandle]:
        """Return current handles filtered by scope or type."""

        with self._lock:
            handles: Iterable[ResourceHandle]
            if scope:
                ids = self._scope_index.get(scope, set())
                handles = (self._handles[rid] for rid in ids if rid in self._handles)
            else:
                handles = self._handles.values()
            result: List[ResourceHandle] = []
            for handle in handles:
                if resource_type and handle.type != resource_type:
                    continue
                result.append(handle)
            return result

    def gc(self, *, now: Optional[datetime] = None) -> List[str]:
        """Remove expired, idle resources. Returns the removed resource ids."""

        now = now or _utcnow()
        removed: List[str] = []
        with self._lock:
            for resource_id, handle in list(self._handles.items()):
                if handle.in_use == 0 and handle.is_expired(now):
                    removed.append(resource_id)
                    self._handles.pop(resource_id, None)
                    if handle.scope:
                        scoped = self._scope_index.get(handle.scope)
                        if scoped:
                            scoped.discard(resource_id)
                            if not scoped:
                                self._scope_index.pop(handle.scope, None)
        return removed

    def to_artifact_descriptor(
        self,
        resource_id: str,
        *,
        inline: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """Build an artifact descriptor for Result payloads."""

        with self._lock:
            handle = self._handles.get(resource_id)
            if not handle:
                raise KeyError(f"resource {resource_id} not found")
        descriptor: Dict[str, Any] = {
            "resource_id": resource_id,
            "worker_id": self._worker_id,
            "type": handle.type,
        }
        if handle.size_bytes is not None:
            descriptor["size_bytes"] = handle.size_bytes
        if inline is not None:
            descriptor["inline"] = inline
        if handle.expires_at is not None:
            descriptor["expires_at"] = handle.expires_at
        metadata: Dict[str, Any] = dict(handle.metadata)
        if handle.path and "path" not in metadata:
            metadata["path"] = str(handle.path)
        if metadata:
            descriptor["metadata"] = metadata
        return descriptor
