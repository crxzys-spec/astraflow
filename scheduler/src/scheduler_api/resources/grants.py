"""Resource grant storage for static resource authorization."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any, Dict, Iterable, List, Optional

from sqlalchemy import select

from scheduler_api.db.models import ResourceGrantRecord
from scheduler_api.db.session import SessionLocal


class ResourceGrantNotFoundError(FileNotFoundError):
    """Raised when a resource grant does not exist."""


@dataclass
class StoredResourceGrant:
    grant_id: str
    resource_id: str
    package_name: str
    resource_key: str
    scope: str
    actions: List[str]
    created_at: datetime
    package_version: Optional[str] = None
    workflow_id: Optional[str] = None
    created_by: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "grant_id": self.grant_id,
            "resource_id": self.resource_id,
            "package_name": self.package_name,
            "package_version": self.package_version,
            "resource_key": self.resource_key,
            "scope": self.scope,
            "workflow_id": self.workflow_id,
            "actions": list(self.actions),
            "created_at": self.created_at.isoformat(),
            "created_by": self.created_by,
            "metadata": self.metadata or {},
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "StoredResourceGrant":
        return cls(
            grant_id=payload["grant_id"],
            resource_id=payload["resource_id"],
            package_name=payload["package_name"],
            package_version=payload.get("package_version"),
            resource_key=payload["resource_key"],
            scope=payload.get("scope") or "workflow",
            workflow_id=payload.get("workflow_id"),
            actions=list(payload.get("actions") or []),
            created_at=_parse_datetime(payload.get("created_at")) or _utcnow(),
            created_by=payload.get("created_by"),
            metadata=payload.get("metadata"),
        )


class ResourceGrantStore:
    def __init__(self) -> None:
        pass

    def create(
        self,
        *,
        resource_id: str,
        package_name: str,
        resource_key: str,
        scope: str,
        actions: List[str],
        package_version: Optional[str] = None,
        workflow_id: Optional[str] = None,
        created_by: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> StoredResourceGrant:
        record = ResourceGrantRecord(
            resource_id=resource_id,
            package_name=package_name,
            package_version=package_version,
            resource_key=resource_key,
            scope=scope,
            workflow_id=workflow_id,
            actions=_serialize_actions(actions),
            created_by=created_by,
            metadata_json=_serialize_metadata(metadata),
        )
        with SessionLocal() as session:
            session.add(record)
            session.commit()
            session.refresh(record)
        return _record_to_grant(record)

    def get(self, grant_id: str) -> StoredResourceGrant:
        with SessionLocal() as session:
            record = session.get(ResourceGrantRecord, grant_id)
            if record is None:
                raise ResourceGrantNotFoundError(grant_id)
            return _record_to_grant(record)

    def delete(self, grant_id: str) -> None:
        with SessionLocal() as session:
            record = session.get(ResourceGrantRecord, grant_id)
            if record is None:
                raise ResourceGrantNotFoundError(grant_id)
            session.delete(record)
            session.commit()

    def list(
        self,
        *,
        created_by: Optional[str] = None,
        workflow_id: Optional[str] = None,
        package_name: Optional[str] = None,
        package_version: Optional[str] = None,
        resource_key: Optional[str] = None,
        resource_id: Optional[str] = None,
        scope: Optional[str] = None,
    ) -> List[StoredResourceGrant]:
        stmt = select(ResourceGrantRecord)
        if created_by:
            stmt = stmt.where(ResourceGrantRecord.created_by == created_by)
        if workflow_id:
            stmt = stmt.where(ResourceGrantRecord.workflow_id == workflow_id)
        if package_name:
            stmt = stmt.where(ResourceGrantRecord.package_name == package_name)
        if package_version:
            stmt = stmt.where(ResourceGrantRecord.package_version == package_version)
        if resource_key:
            stmt = stmt.where(ResourceGrantRecord.resource_key == resource_key)
        if resource_id:
            stmt = stmt.where(ResourceGrantRecord.resource_id == resource_id)
        if scope:
            stmt = stmt.where(ResourceGrantRecord.scope == scope)

        with SessionLocal() as session:
            records = session.execute(stmt).scalars().all()
        return [_record_to_grant(record) for record in records]


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


@lru_cache()
def get_resource_grant_store() -> ResourceGrantStore:
    return ResourceGrantStore()


def _serialize_actions(actions: Iterable[str]) -> str:
    return json.dumps(list(actions), ensure_ascii=True)


def _parse_actions(value: Optional[str]) -> List[str]:
    if not value:
        return []
    try:
        payload = json.loads(value)
    except json.JSONDecodeError:
        return []
    if isinstance(payload, list):
        return [str(item) for item in payload if item is not None]
    return []


def _serialize_metadata(metadata: Optional[Dict[str, Any]]) -> Optional[str]:
    if metadata is None:
        return None
    return json.dumps(metadata, ensure_ascii=True)


def _parse_metadata(value: Optional[str]) -> Optional[Dict[str, Any]]:
    if not value:
        return None
    try:
        payload = json.loads(value)
    except json.JSONDecodeError:
        return None
    if isinstance(payload, dict):
        return payload
    return None


def _record_to_grant(record: ResourceGrantRecord) -> StoredResourceGrant:
    return StoredResourceGrant(
        grant_id=record.id,
        resource_id=record.resource_id,
        package_name=record.package_name,
        package_version=record.package_version,
        resource_key=record.resource_key,
        scope=record.scope,
        workflow_id=record.workflow_id,
        actions=_parse_actions(record.actions),
        created_at=record.created_at,
        created_by=record.created_by,
        metadata=_parse_metadata(record.metadata_json),
    )
