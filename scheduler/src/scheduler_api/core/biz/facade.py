"""Business facade for control-plane run orchestration."""

from __future__ import annotations

from typing import List, Optional, Tuple

from scheduler_api.models.list_runs200_response import ListRuns200Response
from scheduler_api.models.start_run_request import StartRunRequest
from scheduler_api.models.start_run_request_workflow import StartRunRequestWorkflow
from shared.models.biz.exec.error import ExecErrorPayload
from shared.models.biz.exec.feedback import ExecFeedbackPayload
from shared.models.biz.exec.next.request import ExecMiddlewareNextRequest
from shared.models.biz.exec.next.response import ExecMiddlewareNextResponse
from shared.models.biz.exec.result import ExecResultPayload

from .services.run_state_service import DispatchRequest, RunRecord, RunStateService, run_state_service
from .dispatch.orchestrator import RunOrchestrator, run_orchestrator


class ControlPlaneBizFacade:
    """Single entrypoint for business orchestration."""

    def __init__(
        self,
        *,
        coordinator: RunStateService = run_state_service,
        orchestrator: RunOrchestrator = run_orchestrator,
    ) -> None:
        self._coordinator = coordinator
        self._orchestrator = orchestrator

    async def list_runs(
        self,
        *,
        limit: int,
        cursor: Optional[str],
        status: Optional[str],
        client_id: Optional[str],
    ) -> ListRuns200Response:
        return await self._coordinator.to_list_response(
            limit=limit,
            cursor=cursor,
            status=status,
            client_id=client_id,
        )

    async def start_run(
        self,
        *,
        run_id: str,
        request: StartRunRequest,
        tenant: str,
    ) -> tuple[RunRecord, List[DispatchRequest]]:
        record = await self._coordinator.create_run(
            run_id=run_id,
            request=request,
            tenant=tenant,
        )
        ready = await self._coordinator.collect_ready_nodes(run_id)
        if ready:
            await self._orchestrator.enqueue(ready)
        return record, ready

    async def get_run(self, run_id: str) -> Optional[RunRecord]:
        return await self._coordinator.get(run_id)

    async def get_workflow_with_state(self, run_id: str) -> Optional[StartRunRequestWorkflow]:
        return await self._coordinator.get_workflow_with_state(run_id)

    async def cancel_run(
        self,
        run_id: str,
    ) -> tuple[Optional[RunRecord], List[Tuple[str, str, str, Optional[str], Optional[str]]]]:
        record, cancelled_next = await self._coordinator.cancel_run(run_id)
        if record:
            await self._orchestrator.cancel_run(run_id)
        return record, cancelled_next

    async def record_result(
        self,
        payload: ExecResultPayload,
    ) -> tuple[Optional[RunRecord], List[DispatchRequest], List[Tuple[Optional[str], ExecMiddlewareNextResponse]]]:
        record, ready, next_responses = await self._coordinator.record_result(payload.run_id, payload)
        if ready:
            await self._orchestrator.enqueue(ready)
        return record, ready, next_responses

    async def record_feedback(self, payload: ExecFeedbackPayload) -> None:
        await self._coordinator.record_feedback(payload)

    async def handle_next_request(
        self,
        payload: ExecMiddlewareNextRequest,
        *,
        worker_name: Optional[str],
        worker_instance_id: Optional[str],
    ) -> Tuple[List[DispatchRequest], Optional[str]]:
        ready, error = await self._coordinator.handle_next_request(
            payload,
            worker_name=worker_name,
            worker_instance_id=worker_instance_id,
        )
        if ready:
            await self._orchestrator.enqueue(ready)
        return ready, error

    async def resolve_next_response_worker(self, request_id: str) -> Optional[str]:
        return await self._coordinator.resolve_next_response_worker(request_id)

    async def collect_expired_next_requests(self) -> List[Tuple[str, str, str, Optional[str], Optional[str]]]:
        return await self._coordinator.collect_expired_next_requests()

    async def reset_after_worker_cancel(
        self,
        run_id: Optional[str],
        *,
        node_id: Optional[str],
        task_id: Optional[str],
    ) -> Optional[RunRecord]:
        record = await self._coordinator.reset_after_worker_cancel(
            run_id,
            node_id=node_id,
            task_id=task_id,
        )
        if record:
            ready = await self._coordinator.collect_ready_nodes(record.run_id)
            if ready:
                await self._orchestrator.enqueue(ready)
        return record

    async def record_command_error(
        self,
        payload: ExecErrorPayload,
        *,
        run_id: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> tuple[Optional[RunRecord], List[DispatchRequest]]:
        record, ready = await self._coordinator.record_command_error(
            payload=payload,
            run_id=run_id,
            task_id=task_id,
        )
        if ready:
            await self._orchestrator.enqueue(ready)
        return record, ready

    async def register_ack(self, dispatch_id: str) -> None:
        await self._orchestrator.register_ack(dispatch_id)


biz_facade = ControlPlaneBizFacade()
