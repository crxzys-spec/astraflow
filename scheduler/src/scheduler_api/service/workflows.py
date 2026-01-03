"""Service layer for workflow operations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from typing import Optional
import uuid

from pydantic import ValidationError

from scheduler_api.audit import record_audit_event
from scheduler_api.db.models import WorkflowRecord
from scheduler_api.models.list_workflows200_response_items_inner import (
    ListWorkflows200ResponseItemsInner,
)
from scheduler_api.models.persist_workflow201_response import PersistWorkflow201Response
from scheduler_api.models.workflow import Workflow
from scheduler_api.db.session import run_in_session
from scheduler_api.repo.users import UserRepository
from scheduler_api.repo.workflows import WorkflowRepository


class WorkflowError(Exception):
    pass


class WorkflowNotFoundError(WorkflowError):
    def __init__(self, workflow_id: str) -> None:
        super().__init__(f"Workflow '{workflow_id}' was not found.")
        self.workflow_id = workflow_id


class WorkflowPermissionError(WorkflowError):
    pass


class WorkflowValidationError(WorkflowError):
    def __init__(self, error: str, message: str) -> None:
        super().__init__(message)
        self.error = error
        self.message = message


class WorkflowCorruptedError(WorkflowError):
    def __init__(self, workflow_id: str) -> None:
        super().__init__(f"Workflow '{workflow_id}' is stored in an invalid format.")
        self.workflow_id = workflow_id


@dataclass(frozen=True)
class WorkflowPersistResult:
    workflow_id: str
    created: bool
    name: Optional[str]
    namespace: str


class WorkflowService:
    def __init__(
        self,
        repo: Optional[WorkflowRepository] = None,
        users: Optional[UserRepository] = None,
    ) -> None:
        self._repo = repo or WorkflowRepository()
        self._users = users or UserRepository()

    def list_workflows(
        self,
        *,
        limit: int,
        owner_id: Optional[str],
        is_admin: bool,
    ) -> list[Workflow]:
        def _list(session) -> list[Workflow]:
            rows = self._repo.list_active(
                limit=limit,
                owner_id=owner_id,
                is_admin=is_admin,
                session=session,
            )
            items: list[Workflow] = []
            for row in rows:
                try:
                    payload = self._hydrate_payload(row, session=session)
                    definition = Workflow.from_dict(payload)
                except (json.JSONDecodeError, ValueError, ValidationError):  # pragma: no cover - defensive
                    continue
                items.append(definition)
            return items

        return run_in_session(_list)

    def persist_workflow(
        self,
        definition: ListWorkflows200ResponseItemsInner,
        *,
        actor_id: Optional[str],
    ) -> PersistWorkflow201Response:
        if definition is None:
            raise WorkflowValidationError("invalid_payload", "Workflow definition body is required.")

        payload = definition.model_dump(by_alias=True, exclude_none=True)
        workflow_id = payload.get("id") or definition.id
        workflow_id_str = str(workflow_id)
        metadata = payload.get("metadata") or definition.metadata
        if metadata is None:
            raise WorkflowValidationError("invalid_payload", "Workflow metadata is required.")
        metadata_dict = metadata if isinstance(metadata, dict) else metadata.model_dump(
            by_alias=True, exclude_none=True
        )
        workflow_name = metadata_dict.get("name")
        owner_id = actor_id or metadata_dict.get("ownerId")

        structure = self._strip_metadata(payload)
        metadata_snapshot = metadata_dict or {}
        extra_metadata = {
            key: value
            for key, value in metadata_snapshot.items()
            if key
            not in {"name", "description", "environment", "namespace", "originId", "tags", "ownerId"}
        }
        structure["_metaExtra"] = extra_metadata

        def _persist(session) -> WorkflowPersistResult:
            created = False
            record = self._repo.get(workflow_id_str, session=session)
            if record is None:
                created = True
                origin_id = metadata_dict.get("originId") or workflow_id_str
                origin_id_str = str(origin_id) if origin_id is not None else None
                record = WorkflowRecord(
                    id=workflow_id_str,
                    name=workflow_name,
                    definition=json.dumps(structure, ensure_ascii=False, default=str),
                    schema_version=payload.get("schemaVersion") or "2025-10",
                    namespace=metadata_dict.get("namespace") or "default",
                    origin_id=origin_id_str,
                    description=metadata_dict.get("description"),
                    environment=metadata_dict.get("environment"),
                    tags=json.dumps(metadata_dict.get("tags"))
                    if metadata_dict.get("tags")
                    else None,
                    owner_id=owner_id,
                    created_by=actor_id,
                    preview_image=None,
                    updated_by=actor_id,
                )
                self._repo.save(record, session=session)
            else:
                if record.deleted_at is not None:
                    record.deleted_at = None
                record_owner = record.owner_id or record.created_by
                if record_owner and owner_id and record_owner != owner_id:
                    raise WorkflowPermissionError("You do not have access to this workflow.")
                record.name = workflow_name
                record.definition = json.dumps(structure, ensure_ascii=False, default=str)
                record.schema_version = payload.get("schemaVersion") or record.schema_version
                record.namespace = metadata_dict.get("namespace") or record.namespace or "default"
                origin_id = metadata_dict.get("originId") or record.origin_id or workflow_id_str
                record.origin_id = str(origin_id) if origin_id is not None else None
                record.description = metadata_dict.get("description")
                record.environment = metadata_dict.get("environment")
                record.tags = (
                    json.dumps(metadata_dict.get("tags"))
                    if metadata_dict.get("tags")
                    else None
                )
                if owner_id:
                    record.owner_id = owner_id
                if actor_id:
                    record.updated_by = actor_id
            return WorkflowPersistResult(
                workflow_id=workflow_id_str,
                created=created,
                name=workflow_name,
                namespace=metadata_dict.get("namespace") or record.namespace or "default",
            )

        result = run_in_session(_persist)
        record_audit_event(
            actor_id=actor_id,
            action="workflow.create" if result.created else "workflow.update",
            target_type="workflow",
            target_id=result.workflow_id,
            metadata={"name": result.name, "namespace": result.namespace},
        )
        return PersistWorkflow201Response(workflow_id=result.workflow_id)

    def get_workflow(
        self,
        workflow_id: str,
        *,
        owner_id: Optional[str],
        is_admin: bool,
    ) -> Workflow:
        def _get(session) -> dict[str, object]:
            record = self._repo.get(workflow_id, session=session)
            if record is None or record.deleted_at is not None:
                raise WorkflowNotFoundError(workflow_id)
            if not is_admin and owner_id and not self._owns_record(record, owner_id):
                raise WorkflowPermissionError("You do not have access to this workflow.")
            return self._hydrate_payload(record, session=session)

        try:
            payload = run_in_session(_get)
            return Workflow.from_dict(payload)
        except (json.JSONDecodeError, ValueError, ValidationError) as exc:  # pragma: no cover - defensive
            raise WorkflowCorruptedError(workflow_id) from exc

    def delete_workflow(
        self,
        workflow_id: str,
        *,
        owner_id: Optional[str],
        is_admin: bool,
        actor_id: Optional[str],
    ) -> None:
        def _delete(session) -> tuple[Optional[str], str]:
            record = self._repo.get(workflow_id, session=session)
            if record is None or record.deleted_at is not None:
                raise WorkflowNotFoundError(workflow_id)
            if not is_admin and not self._owns_record(record, owner_id):
                raise WorkflowPermissionError("You do not have access to this workflow.")
            record.deleted_at = datetime.now(timezone.utc)
            if actor_id:
                record.updated_by = actor_id
            return record.name, record.namespace or "default"

        workflow_name, namespace = run_in_session(_delete)
        record_audit_event(
            actor_id=actor_id,
            action="workflow.delete",
            target_type="workflow",
            target_id=workflow_id,
            metadata={"name": workflow_name, "namespace": namespace},
        )

    def get_workflow_preview(self, workflow_id: str) -> Optional[str]:
        def _get(session) -> Optional[str]:
            record = self._repo.get(workflow_id, session=session)
            if record is None or record.deleted_at is not None:
                raise WorkflowNotFoundError(workflow_id)
            return record.preview_image

        return run_in_session(_get)

    def set_workflow_preview(
        self,
        workflow_id: str,
        *,
        preview_image: Optional[str],
        actor_id: Optional[str],
    ) -> Optional[str]:
        def _update(session) -> Optional[str]:
            record = self._repo.get(workflow_id, session=session)
            if record is None or record.deleted_at is not None:
                raise WorkflowNotFoundError(workflow_id)
            record.preview_image = preview_image
            if actor_id:
                record.updated_by = actor_id
            return record.preview_image

        return run_in_session(_update)

    def hydrate_payload(
        self,
        record: WorkflowRecord,
        *,
        session=None,
    ) -> dict[str, object]:
        if session is None:
            def _hydrate(session) -> dict[str, object]:
                return self._hydrate_payload(record, session=session)

            return run_in_session(_hydrate)
        return self._hydrate_payload(record, session=session)

    def _hydrate_payload(self, record: WorkflowRecord, *, session) -> dict[str, object]:
        try:
            structure = json.loads(record.definition)
        except json.JSONDecodeError:
            structure = {}
        extra_meta = structure.pop("_metaExtra", {})
        if not isinstance(extra_meta, dict):
            extra_meta = {}
        metadata = {
            "name": record.name,
            "description": record.description,
            "environment": record.environment,
            "namespace": record.namespace or "default",
            "originId": record.origin_id or record.id,
        }
        metadata.update(extra_meta)
        owner_value = record.owner_id or record.created_by
        if owner_value:
            metadata["ownerId"] = owner_value
            owner_name = self._users.get_display_name(owner_value, session=session)
            if owner_name:
                metadata["ownerName"] = owner_name
        if record.created_by:
            metadata["createdBy"] = record.created_by
        if record.updated_by:
            metadata["updatedBy"] = record.updated_by
        if record.tags:
            try:
                metadata["tags"] = json.loads(record.tags)
            except json.JSONDecodeError:
                pass
        payload = {
            **structure,
            "id": record.id,
            "schemaVersion": record.schema_version or "2025-10",
            "metadata": metadata,
            "previewImage": record.preview_image,
        }
        return self._ensure_uuid_fields(payload)

    @staticmethod
    def _ensure_uuid(value: Optional[str], salt: str) -> str:
        try:
            return str(uuid.UUID(str(value)))
        except Exception:
            return str(uuid.uuid5(uuid.NAMESPACE_URL, f"{salt}:{value}"))

    @classmethod
    def _ensure_uuid_fields(cls, payload: dict[str, object]) -> dict[str, object]:
        payload = dict(payload)
        payload["id"] = cls._ensure_uuid(payload.get("id"), "workflow")
        metadata = payload.get("metadata")
        if isinstance(metadata, dict):
            origin = metadata.get("originId")
            metadata["originId"] = cls._ensure_uuid(origin, "origin")
            payload["metadata"] = metadata

        def _fix_node_list(nodes: list[dict[str, object]]) -> list[dict[str, object]]:
            fixed: list[dict[str, object]] = []
            for node in nodes:
                if not isinstance(node, dict):
                    continue
                entry = dict(node)
                entry["id"] = cls._ensure_uuid(entry.get("id"), "node")
                entry["schema"] = entry["schema"] if isinstance(entry.get("schema"), dict) else None
                fixed.append(entry)
            return fixed

        def _fix_edges(edges: list[dict[str, object]]) -> list[dict[str, object]]:
            fixed: list[dict[str, object]] = []
            for edge in edges:
                if not isinstance(edge, dict):
                    continue
                entry = dict(edge)
                entry["id"] = cls._ensure_uuid(entry.get("id"), "edge")
                source = entry.get("source")
                if isinstance(source, dict):
                    source = dict(source)
                    source["node"] = cls._ensure_uuid(source.get("node"), "edge-src")
                    entry["source"] = source
                target = entry.get("target")
                if isinstance(target, dict):
                    target = dict(target)
                    target["node"] = cls._ensure_uuid(target.get("node"), "edge-tgt")
                    entry["target"] = target
                fixed.append(entry)
            return fixed

        if isinstance(payload.get("nodes"), list):
            payload["nodes"] = _fix_node_list(payload["nodes"])  # type: ignore[index]
        if isinstance(payload.get("edges"), list):
            payload["edges"] = _fix_edges(payload["edges"])  # type: ignore[index]

        if isinstance(payload.get("subgraphs"), list):
            subgraphs = []
            for sub in payload["subgraphs"]:  # type: ignore[index]
                if not isinstance(sub, dict):
                    continue
                sub_entry = dict(sub)
                sub_entry["id"] = cls._ensure_uuid(sub_entry.get("id"), "subgraph")
                definition = sub_entry.get("definition")
                if isinstance(definition, dict):
                    def_entry = dict(definition)
                    if "schema" in def_entry and not isinstance(def_entry.get("schema"), dict):
                        def_entry["schema"] = None
                    if isinstance(def_entry.get("nodes"), list):
                        def_entry["nodes"] = _fix_node_list(def_entry["nodes"])  # type: ignore[index]
                    if isinstance(def_entry.get("edges"), list):
                        def_entry["edges"] = _fix_edges(def_entry["edges"])  # type: ignore[index]
                    sub_entry["definition"] = def_entry
                subgraphs.append(sub_entry)
            payload["subgraphs"] = subgraphs
        return payload

    @staticmethod
    def _strip_metadata(payload: dict[str, object]) -> dict[str, object]:
        return {
            key: value
            for key, value in payload.items()
            if key not in {"id", "schemaVersion", "metadata", "previewImage"}
        }

    @staticmethod
    def _owns_record(record: WorkflowRecord, owner_id: Optional[str]) -> bool:
        if not owner_id:
            return False
        return (record.owner_id == owner_id) or (
            record.owner_id is None and record.created_by == owner_id
        )


__all__ = [
    "WorkflowService",
    "WorkflowError",
    "WorkflowNotFoundError",
    "WorkflowPermissionError",
    "WorkflowValidationError",
    "WorkflowCorruptedError",
]
