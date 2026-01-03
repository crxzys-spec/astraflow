"""Database-backed resource record repositories for storage providers."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import or_, select

from scheduler_api.db.models import ResourcePayloadRecord, ResourceRecord
from scheduler_api.db.session import SessionLocal


class ResourceRecordRepository:
    def get(self, resource_id: str) -> Optional[ResourceRecord]:
        with SessionLocal() as session:
            return session.get(ResourceRecord, resource_id)

    def upsert(self, record: ResourceRecord) -> ResourceRecord:
        with SessionLocal() as session:
            merged = session.merge(record)
            session.commit()
            session.refresh(merged)
            return merged

    def delete(self, resource_id: str) -> None:
        with SessionLocal() as session:
            record = session.get(ResourceRecord, resource_id)
            if record is None:
                return
            session.delete(record)
            session.commit()

    def list_ids(self, *, provider: Optional[str] = None) -> set[str]:
        stmt = select(ResourceRecord.resource_id)
        if provider:
            stmt = stmt.where(ResourceRecord.provider == provider)
        with SessionLocal() as session:
            records = session.execute(stmt).scalars().all()
        return set(records)

    def list(
        self,
        *,
        provider: str,
        owner_id: Optional[str] = None,
        search: Optional[str] = None,
        require_payload: bool = False,
    ) -> list[ResourceRecord]:
        stmt = select(ResourceRecord).where(ResourceRecord.provider == provider)
        if owner_id:
            stmt = stmt.where(ResourceRecord.owner_id == owner_id)
        search_value = (search or "").strip()
        if search_value:
            pattern = f"%{search_value}%"
            stmt = stmt.where(
                or_(
                    ResourceRecord.filename.ilike(pattern),
                    ResourceRecord.resource_id.ilike(pattern),
                )
            )
        if require_payload:
            stmt = stmt.join(
                ResourcePayloadRecord,
                ResourcePayloadRecord.resource_id == ResourceRecord.resource_id,
            )
        with SessionLocal() as session:
            records = session.execute(stmt).scalars().all()
        return list(records)

    def find_by_sha256(
        self,
        *,
        provider: str,
        sha256: str,
        require_payload: bool = False,
    ) -> Optional[ResourceRecord]:
        stmt = select(ResourceRecord).where(
            ResourceRecord.sha256 == sha256,
            ResourceRecord.provider == provider,
        )
        if require_payload:
            stmt = stmt.join(
                ResourcePayloadRecord,
                ResourcePayloadRecord.resource_id == ResourceRecord.resource_id,
            )
        with SessionLocal() as session:
            return session.execute(stmt).scalars().first()


class ResourcePayloadRepository:
    def get(self, resource_id: str) -> Optional[ResourcePayloadRecord]:
        with SessionLocal() as session:
            return session.get(ResourcePayloadRecord, resource_id)

    def exists(self, resource_id: str) -> bool:
        return self.get(resource_id) is not None

    def get_bytes(self, resource_id: str) -> Optional[bytes]:
        record = self.get(resource_id)
        return record.payload if record is not None else None

    def upsert(self, record: ResourcePayloadRecord) -> ResourcePayloadRecord:
        with SessionLocal() as session:
            merged = session.merge(record)
            session.commit()
            session.refresh(merged)
            return merged

    def delete(self, resource_id: str) -> None:
        with SessionLocal() as session:
            record = session.get(ResourcePayloadRecord, resource_id)
            if record is None:
                return
            session.delete(record)
            session.commit()


__all__ = ["ResourcePayloadRepository", "ResourceRecordRepository"]
