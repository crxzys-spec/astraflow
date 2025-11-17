from __future__ import annotations

import json
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select

from scheduler_api.db.models import WorkflowRecord
from scheduler_api.db.session import SessionLocal
from scheduler_api.apis.workflows_api_base import BaseWorkflowsApi
from scheduler_api.models.list_workflows200_response import ListWorkflows200Response
from scheduler_api.models.list_workflows200_response_items_inner import (
    ListWorkflows200ResponseItemsInner,
)
from scheduler_api.models.persist_workflow201_response import PersistWorkflow201Response
from scheduler_api.models.start_run400_response import StartRun400Response


class WorkflowsApiImpl(BaseWorkflowsApi):
    async def list_workflows(
        self,
        limit: Optional[int],
        cursor: Optional[str],
    ) -> ListWorkflows200Response:
        del cursor  # pagination cursor reserved for future implementation
        page_size = limit or 50

        with SessionLocal() as session:
            stmt = (
                select(WorkflowRecord)
                .order_by(WorkflowRecord.created_at.desc())
                .limit(page_size)
            )
            rows = session.execute(stmt).scalars().all()

        items: list[ListWorkflows200ResponseItemsInner] = []
        for row in rows:
            try:
                payload = self._hydrate_payload(row)
                definition = ListWorkflows200ResponseItemsInner.from_json(json.dumps(payload))
            except (json.JSONDecodeError, ValueError):  # pragma: no cover - defensive
                continue
            items.append(definition)

        return ListWorkflows200Response(items=items, next_cursor=None)

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

        workflow_json = list_workflows200_response_items_inner.to_json()
        workflow_id = list_workflows200_response_items_inner.id
        metadata = list_workflows200_response_items_inner.metadata
        if metadata is None:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail=StartRun400Response(
                    error="invalid_payload",
                    message="Workflow metadata is required.",
                ).model_dump(by_alias=True),
            )
        workflow_name = metadata.name

        payload = json.loads(workflow_json)
        structure = self._strip_metadata(payload)

        with SessionLocal() as session:
            record = session.get(WorkflowRecord, workflow_id)
            if record is None:
                record = WorkflowRecord(
                    id=workflow_id,
                    name=workflow_name,
                    definition=json.dumps(structure, ensure_ascii=False),
                    schema_version=payload.get("schemaVersion") or "2025-10",
                    namespace=metadata.namespace or "default",
                    origin_id=metadata.origin_id or workflow_id,
                    description=metadata.description,
                    environment=metadata.environment,
                    tags=json.dumps(metadata.tags) if metadata.tags else None,
                )
                session.add(record)
            else:
                record.name = workflow_name
                record.definition = json.dumps(structure, ensure_ascii=False)
                record.schema_version = payload.get("schemaVersion") or record.schema_version
                record.namespace = metadata.namespace or record.namespace or "default"
                record.origin_id = metadata.origin_id or record.origin_id or workflow_id
                record.description = metadata.description
                record.environment = metadata.environment
                record.tags = json.dumps(metadata.tags) if metadata.tags else None
            session.commit()

        return PersistWorkflow201Response(workflow_id=workflow_id)

    async def get_workflow(
        self,
        workflowId: str,
    ) -> ListWorkflows200ResponseItemsInner:
        with SessionLocal() as session:
            record = session.get(WorkflowRecord, workflowId)

        if record is None:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                detail=StartRun400Response(
                    error="workflow_not_found",
                    message=f"Workflow '{workflowId}' was not found.",
                ).model_dump(by_alias=True),
            )

        try:
            payload = self._hydrate_payload(record)
            return ListWorkflows200ResponseItemsInner.from_json(json.dumps(payload))
        except (json.JSONDecodeError, ValueError) as exc:  # pragma: no cover - defensive
            raise HTTPException(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=StartRun400Response(
                    error="workflow_corrupted",
                    message=f"Workflow '{workflowId}' is stored in an invalid format.",
                ).model_dump(by_alias=True),
            ) from exc

    @staticmethod
    def _hydrate_payload(record: WorkflowRecord) -> dict[str, object]:
        try:
            structure = json.loads(record.definition)
        except json.JSONDecodeError:
            structure = {}
        metadata = {
            "name": record.name,
            "description": record.description,
            "environment": record.environment,
            "namespace": record.namespace or "default",
            "originId": record.origin_id or record.id,
        }
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
        return payload

    @staticmethod
    def _strip_metadata(payload: dict[str, object]) -> dict[str, object]:
        return {key: value for key, value in payload.items() if key not in {"id", "schemaVersion", "metadata"}}
