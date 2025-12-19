from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from fastapi import HTTPException, status

from scheduler_api.apis.runs_api_base import BaseRunsApi
from scheduler_api.audit import record_audit_event
from scheduler_api.auth.roles import RUN_VIEW_ROLES, WORKFLOW_EDIT_ROLES, require_roles
from scheduler_api.models.list_runs200_response import ListRuns200Response
from scheduler_api.models.list_runs200_response_items_inner import ListRuns200ResponseItemsInner
from scheduler_api.models.start_run202_response import StartRun202Response
from scheduler_api.models.start_run_request import StartRunRequest
from scheduler_api.models.run_start_request import RunStartRequest
from scheduler_api.models.start_run_request_workflow import StartRunRequestWorkflow
from scheduler_api.models.start_run_request_workflow_nodes_inner import (
    StartRunRequestWorkflowNodesInner,
)
from scheduler_api.models.workflow import Workflow

from ..control_plane.orchestrator import run_orchestrator
from ..control_plane.run_registry import run_registry

LOGGER = logging.getLogger(__name__)


class RunsApiImpl(BaseRunsApi):
    """Run orchestration API backed by the webSocket control plane."""

    def __init__(self, tenant: str = "default") -> None:
        self.tenant = tenant

    async def list_runs(
        self,
        limit: Optional[int],
        cursor: Optional[str],
        status: Optional[str],
        client_id: Optional[str],
    ) -> ListRuns200Response:
        require_roles(*RUN_VIEW_ROLES)
        capped_limit = limit or 50
        return await run_registry.to_list_response(
            limit=capped_limit,
            cursor=cursor,
            status=status,
            client_id=client_id,
        )

    async def start_run(
        self,
        start_run_request: RunStartRequest,
        idempotency_key: Optional[str],
    ) -> StartRun202Response:
        token = require_roles(*WORKFLOW_EDIT_ROLES)
        if start_run_request is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="start_run_request body is required",
            )

        # Convert the public request (Workflow1/UUID ids) into the internal model
        payload = start_run_request.model_dump(by_alias=True, exclude_none=True, mode="json")
        start_run_request = StartRunRequest.from_dict(payload)

        workflow = start_run_request.workflow
        self._ensure_initial_node(workflow)

        run_id = str(uuid4())
        record = await run_registry.create_run(
            run_id=run_id,
            request=start_run_request,
            tenant=self.tenant,
        )

        ready = await run_registry.collect_ready_nodes(run_id)
        if ready:
            await run_orchestrator.enqueue(ready)
        LOGGER.info(
            "Run %s queued with %d initial nodes", run_id, len(ready)
        )
        record_audit_event(
            actor_id=token.sub if token else None,
            action="run.start",
            target_type="run",
            target_id=run_id,
            metadata={
                "workflowId": getattr(workflow, "id", None),
                "clientId": start_run_request.client_id,
            },
        )
        return record.to_start_response()

    async def get_run(
        self,
        runId: str,
    ) -> ListRuns200ResponseItemsInner:
        require_roles(*RUN_VIEW_ROLES)
        record = await run_registry.get(runId)
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Run {runId} not found",
            )
        return record.to_summary()

    async def cancel_run(
        self,
        runId: str,
    ) -> StartRun202Response:
        token = require_roles(*WORKFLOW_EDIT_ROLES)
        record, cancelled_next = await run_registry.cancel_run(runId)
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Run {runId} not found",
            )
        await run_orchestrator.cancel_run(runId)
        if cancelled_next:
            await self._notify_cancelled_next(cancelled_next, tenant=self.tenant)
        record_audit_event(
            actor_id=token.sub if token else None,
            action="run.cancel",
            target_type="run",
            target_id=runId,
        )
        return record.to_start_response()

    @staticmethod
    async def _notify_cancelled_next(
        cancelled: list[tuple[str, str, str, Optional[str], Optional[str]]],
        *,
        tenant: str,
    ) -> None:
        """Notify workers waiting on middleware.next when the run is cancelled."""

        from uuid import uuid4  # local import to avoid cycle

        from scheduler_api.control_plane.manager import worker_manager  # late import
        from shared.models.session import Role, Sender, WsEnvelope
        from shared.models.biz.exec.next.response import ExecMiddlewareNextResponse

        for request_id, worker_key, run_id, node_id, middleware_id in cancelled:
            payload = ExecMiddlewareNextResponse(
                requestId=request_id,
                runId=run_id or "",
                nodeId=node_id or "",
                middlewareId=middleware_id or "",
                error={"code": "next_cancelled", "message": run_registry.get_next_error_message("next_cancelled")},
            )
            envelope = WsEnvelope(
                type="biz.exec.next.response",
                id=str(uuid4()),
                ts=datetime.now(timezone.utc),
                corr=request_id,
                seq=None,
                tenant=tenant,
                sender=Sender(role=Role.scheduler, id=worker_manager.scheduler_id),
                payload=payload.model_dump(by_alias=True, exclude_none=True),
            )
            await worker_manager.send_envelope(worker_key, envelope)

    async def get_run_definition(
        self,
        runId: str,
    ) -> Workflow:
        require_roles(*RUN_VIEW_ROLES)
        workflow = await run_registry.get_workflow_with_state(runId)
        if not workflow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Run {runId} not found",
            )
        # Normalize to the public Workflow model to satisfy response validation and avoid
        # leaking internal BaseModel attributes (e.g. .schema method) into the payload.
        return Workflow.from_dict(workflow.to_dict())

    def _ensure_initial_node(self, workflow: StartRunRequestWorkflow) -> None:
        self._select_initial_node(workflow)

    def _select_initial_node(self, workflow: StartRunRequestWorkflow) -> StartRunRequestWorkflowNodesInner:
        for node in workflow.nodes:
            if node.package and node.package.name and node.package.version:
                return node
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Workflow must contain at least one node with package metadata",
        )
