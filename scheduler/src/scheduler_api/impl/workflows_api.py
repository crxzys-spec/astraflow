from __future__ import annotations

from datetime import datetime, timezone
import json
from typing import Optional
import uuid

from fastapi import HTTPException, status
from pydantic import ValidationError
from sqlalchemy import and_, or_, select

from scheduler_api.audit import record_audit_event
from scheduler_api.auth.roles import WORKFLOW_EDIT_ROLES, WORKFLOW_VIEW_ROLES, require_roles
from scheduler_api.db.models import WorkflowRecord, UserRecord
from scheduler_api.db.session import SessionLocal
from scheduler_api.apis.workflows_api_base import BaseWorkflowsApi
from scheduler_api.models.list_workflows200_response_items_inner import (
    ListWorkflows200ResponseItemsInner,
)
from scheduler_api.models.persist_workflow201_response import PersistWorkflow201Response
from scheduler_api.models.start_run400_response import StartRun400Response
from scheduler_api.models.workflow import Workflow
from scheduler_api.models.workflow_list import WorkflowList
from scheduler_api.models.workflow_preview import WorkflowPreview


class WorkflowsApiImpl(BaseWorkflowsApi):
    async def list_workflows(
        self,
        limit: Optional[int],
        cursor: Optional[str],
    ) -> WorkflowList:
        del cursor  # pagination cursor reserved for future implementation
        token = require_roles(*WORKFLOW_VIEW_ROLES)
        page_size = limit or 50
        is_admin = "admin" in (token.roles if token else [])
        owner_id = token.sub if token else None

        with SessionLocal() as session:
            stmt = (
                select(WorkflowRecord)
                .where(WorkflowRecord.deleted_at.is_(None))
                .order_by(WorkflowRecord.created_at.desc())
                .limit(page_size)
            )
            if not is_admin and owner_id:
                stmt = stmt.where(
                    or_(
                        WorkflowRecord.owner_id == owner_id,
                        and_(
                            WorkflowRecord.owner_id.is_(None),
                            WorkflowRecord.created_by == owner_id,
                        ),
                    )
            )
            rows = session.execute(stmt).scalars().all()

        items: list[Workflow1] = []
        for row in rows:
            try:
                payload = self._hydrate_payload(row)
                definition = Workflow.from_dict(payload)
            except (json.JSONDecodeError, ValueError, ValidationError):  # pragma: no cover - defensive
                continue
            items.append(definition)

        return WorkflowList(items=items, next_cursor=None)

    async def persist_workflow(
        self,
        list_workflows200_response_items_inner: ListWorkflows200ResponseItemsInner,
        idempotency_key: Optional[str],
    ) -> PersistWorkflow201Response:
        del idempotency_key  # reserved for future enhancement
        if list_workflows200_response_items_inner is None:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail=StartRun400Response(
                    error="invalid_payload",
                    message="Workflow definition body is required.",
                ).model_dump(by_alias=True),
            )

        payload = list_workflows200_response_items_inner.model_dump(by_alias=True, exclude_none=True)
        workflow_id = payload.get("id") or list_workflows200_response_items_inner.id
        workflow_id_str = str(workflow_id)
        metadata = payload.get("metadata") or list_workflows200_response_items_inner.metadata
        if metadata is None:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail=StartRun400Response(
                    error="invalid_payload",
                    message="Workflow metadata is required.",
                ).model_dump(by_alias=True),
            )
        metadata_dict = metadata if isinstance(metadata, dict) else metadata.model_dump(by_alias=True, exclude_none=True)
        workflow_name = metadata_dict.get("name")
        token = require_roles(*WORKFLOW_EDIT_ROLES)
        owner_id = token.sub if token else metadata_dict.get("ownerId")

        structure = self._strip_metadata(payload)
        # Preserve metadata fields that are not stored column-by-column so we can roundtrip them
        metadata_snapshot = metadata_dict or {}
        extra_metadata = {
            key: value
            for key, value in metadata_snapshot.items()
            if key not in {"name", "description", "environment", "namespace", "originId", "tags", "ownerId"}
        }
        structure["_metaExtra"] = extra_metadata

        created = False
        with SessionLocal() as session:
            record = session.get(WorkflowRecord, workflow_id_str)
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
                    tags=json.dumps(metadata_dict.get("tags")) if metadata_dict.get("tags") else None,
                    owner_id=owner_id,
                    created_by=token.sub if token else None,
                    preview_image=None,
                    updated_by=token.sub if token else None,
                )
                session.add(record)
            else:
                if record.deleted_at is not None:
                    record.deleted_at = None
                record_owner = record.owner_id or record.created_by
                if record_owner and owner_id and record_owner != owner_id:
                    raise HTTPException(
                        status.HTTP_403_FORBIDDEN,
                        detail=StartRun400Response(
                            error="forbidden",
                            message="You do not have access to this workflow.",
                        ).model_dump(by_alias=True),
                    )
                record.name = workflow_name
                record.definition = json.dumps(structure, ensure_ascii=False, default=str)
                record.schema_version = payload.get("schemaVersion") or record.schema_version
                record.namespace = metadata_dict.get("namespace") or record.namespace or "default"
                origin_id = metadata_dict.get("originId") or record.origin_id or workflow_id_str
                record.origin_id = str(origin_id) if origin_id is not None else None
                record.description = metadata_dict.get("description")
                record.environment = metadata_dict.get("environment")
                record.tags = (
                    json.dumps(metadata_dict.get("tags")) if metadata_dict.get("tags") else None
                )
                # preview image is managed via a dedicated endpoint; keep existing value
                if owner_id:
                    record.owner_id = owner_id
                if token:
                    record.updated_by = token.sub
            session.commit()

        record_audit_event(
            actor_id=token.sub if token else None,
            action="workflow.create" if created else "workflow.update",
            target_type="workflow",
            target_id=workflow_id_str,
            metadata={"name": workflow_name, "namespace": metadata_dict.get("namespace") or "default"},
        )

        return PersistWorkflow201Response(workflow_id=workflow_id_str)

    async def get_workflow(
        self,
        workflowId: str,
    ) -> Workflow1:
        token = require_roles(*WORKFLOW_VIEW_ROLES)
        is_admin = "admin" in (token.roles if token else [])
        owner_id = token.sub if token else None

        with SessionLocal() as session:
            record = session.get(WorkflowRecord, workflowId)

        if record is None or record.deleted_at is not None:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                detail=StartRun400Response(
                    error="workflow_not_found",
                    message=f"Workflow '{workflowId}' was not found.",
                ).model_dump(by_alias=True),
            )
        if not is_admin and owner_id and not self._owns_record(record, owner_id):
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                detail=StartRun400Response(
                    error="forbidden",
                    message="You do not have access to this workflow.",
                ).model_dump(by_alias=True),
            )

        try:
            payload = self._hydrate_payload(record)
            return Workflow.from_dict(payload)
        except (json.JSONDecodeError, ValueError, ValidationError) as exc:  # pragma: no cover - defensive
            raise HTTPException(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=StartRun400Response(
                    error="workflow_corrupted",
                    message=f"Workflow '{workflowId}' is stored in an invalid format.",
                ).model_dump(by_alias=True),
            ) from exc

    async def delete_workflow(
        self,
        workflowId: str,
    ) -> None:
        token = require_roles(*WORKFLOW_EDIT_ROLES)
        is_admin = "admin" in (token.roles if token else [])
        owner_id = token.sub if token else None

        with SessionLocal() as session:
            record = session.get(WorkflowRecord, workflowId)
            if record is None or record.deleted_at is not None:
                raise HTTPException(
                    status.HTTP_404_NOT_FOUND,
                    detail=StartRun400Response(
                        error="workflow_not_found",
                        message=f"Workflow '{workflowId}' was not found.",
                    ).model_dump(by_alias=True),
                )
            if not is_admin and not self._owns_record(record, owner_id):
                raise HTTPException(
                    status.HTTP_403_FORBIDDEN,
                    detail=StartRun400Response(
                        error="forbidden",
                        message="You do not have access to this workflow.",
                    ).model_dump(by_alias=True),
                )

            record.deleted_at = datetime.now(timezone.utc)
            if token:
                record.updated_by = token.sub
            workflow_name = record.name
            workflow_namespace = record.namespace or "default"
            session.commit()

        record_audit_event(
            actor_id=token.sub if token else None,
            action="workflow.delete",
            target_type="workflow",
            target_id=workflowId,
            metadata={"name": workflow_name, "namespace": workflow_namespace},
        )

    @staticmethod
    def _hydrate_payload(record: WorkflowRecord) -> dict[str, object]:
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
            owner_name = WorkflowsApiImpl._lookup_user_name(owner_value)
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
        }
        payload = WorkflowsApiImpl._ensure_uuid_fields(payload)
        return payload

    @staticmethod
    def _ensure_uuid(value: Optional[str], salt: str) -> str:
        try:
            return str(uuid.UUID(str(value)))
        except Exception:
            return str(uuid.uuid5(uuid.NAMESPACE_URL, f"{salt}:{value}"))

    @staticmethod
    def _ensure_uuid_fields(payload: dict[str, object]) -> dict[str, object]:
        """Coerce workflow/node/edge ids to UUID strings to satisfy response models."""

        payload = dict(payload)
        payload["id"] = WorkflowsApiImpl._ensure_uuid(payload.get("id"), "workflow")
        metadata = payload.get("metadata")
        if isinstance(metadata, dict):
            origin = metadata.get("originId")
            metadata["originId"] = WorkflowsApiImpl._ensure_uuid(origin, "origin")
            payload["metadata"] = metadata

        def _fix_node_list(nodes: list[dict[str, object]]) -> list[dict[str, object]]:
            fixed: list[dict[str, object]] = []
            for node in nodes:
                if not isinstance(node, dict):
                    continue
                entry = dict(node)
                entry["id"] = WorkflowsApiImpl._ensure_uuid(entry.get("id"), "node")
                # force schema to a concrete dict or null to avoid leaking BaseModel.schema
                entry["schema"] = entry["schema"] if isinstance(entry.get("schema"), dict) else None
                fixed.append(entry)
            return fixed

        def _fix_edges(edges: list[dict[str, object]]) -> list[dict[str, object]]:
            fixed: list[dict[str, object]] = []
            for edge in edges:
                if not isinstance(edge, dict):
                    continue
                entry = dict(edge)
                entry["id"] = WorkflowsApiImpl._ensure_uuid(entry.get("id"), "edge")
                source = entry.get("source")
                if isinstance(source, dict):
                    source = dict(source)
                    source["node"] = WorkflowsApiImpl._ensure_uuid(source.get("node"), "edge-src")
                    entry["source"] = source
                target = entry.get("target")
                if isinstance(target, dict):
                    target = dict(target)
                    target["node"] = WorkflowsApiImpl._ensure_uuid(target.get("node"), "edge-tgt")
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
                sub_entry["id"] = WorkflowsApiImpl._ensure_uuid(sub_entry.get("id"), "subgraph")
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
    def _lookup_user_name(user_id: Optional[str]) -> Optional[str]:
        if not user_id:
            return None
        with SessionLocal() as session:
            user = session.get(UserRecord, user_id)
            return user.display_name if user else None

    @staticmethod
    def _owns_record(record: WorkflowRecord, owner_id: Optional[str]) -> bool:
        if not owner_id:
            return False
        return (record.owner_id == owner_id) or (
            record.owner_id is None and record.created_by == owner_id
        )

    async def get_workflow_preview(self, workflowId: str) -> WorkflowPreview:
        require_roles(*WORKFLOW_VIEW_ROLES)
        with SessionLocal() as session:
            record = session.get(WorkflowRecord, workflowId)
            if record is None or record.deleted_at is not None:
                raise HTTPException(
                    status.HTTP_404_NOT_FOUND,
                    detail="Workflow not found",
                )
            return WorkflowPreview(preview_image=record.preview_image)

    async def set_workflow_preview(self, workflowId: str, payload: WorkflowPreview) -> WorkflowPreview:
        token = require_roles(*WORKFLOW_EDIT_ROLES)
        with SessionLocal() as session:
            record = session.get(WorkflowRecord, workflowId)
            if record is None or record.deleted_at is not None:
                raise HTTPException(
                    status.HTTP_404_NOT_FOUND,
                    detail="Workflow not found",
                )
            preview_value = None
            if payload and isinstance(payload.preview_image, str):
                preview_value = payload.preview_image
            record.preview_image = preview_value
            if token:
                record.updated_by = token.sub
            session.commit()
            return WorkflowPreview(preview_image=record.preview_image)
