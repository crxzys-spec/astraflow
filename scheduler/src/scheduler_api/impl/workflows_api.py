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
                definition = ListWorkflows200ResponseItemsInner.from_json(row.definition)
            except (json.JSONDecodeError, ValueError) as exc:  # pragma: no cover - defensive
                # Skip corrupted entries but continue processing others
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

        with SessionLocal() as session:
            record = session.get(WorkflowRecord, workflow_id)
            if record is None:
                record = WorkflowRecord(
                    id=workflow_id,
                    name=workflow_name,
                    definition=workflow_json,
                )
                session.add(record)
            else:
                record.name = workflow_name
                record.definition = workflow_json
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
            return ListWorkflows200ResponseItemsInner.from_json(record.definition)
        except (json.JSONDecodeError, ValueError) as exc:  # pragma: no cover - defensive
            raise HTTPException(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=StartRun400Response(
                    error="workflow_corrupted",
                    message=f"Workflow '{workflowId}' is stored in an invalid format.",
                ).model_dump(by_alias=True),
            ) from exc
