"""Background dispatcher for run scheduling."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from shared.models.ws.error import ErrorPayload
from shared.models.ws.cmd.dispatch import Affinity, CommandDispatchPayload, Constraints, ResourceRef

from .manager import WorkerSession, worker_manager
from .run_registry import DispatchRequest, FINAL_STATUSES, run_registry
from scheduler_api.models.workflow_node import WorkflowNode

LOGGER = logging.getLogger(__name__)


class RunOrchestrator:
    def __init__(
        self,
        *,
        max_attempts: int = 5,
        base_retry_seconds: float = 1.0,
        max_retry_seconds: float = 30.0,
        ack_timeout_seconds: float = 5.0,
    ) -> None:
        self._queue: asyncio.Queue[DispatchRequest] = asyncio.Queue()
        self._loop_task: Optional[asyncio.Task[None]] = None
        self._max_attempts = max_attempts
        self._base_retry_seconds = base_retry_seconds
        self._max_retry_seconds = max_retry_seconds
        self._ack_timeout_seconds = ack_timeout_seconds
        self._pending_acks: Dict[str, DispatchRequest] = {}
        self._ack_waiters: Dict[str, asyncio.Task[None]] = {}
        self._ack_lock = asyncio.Lock()

    def ensure_started(self) -> None:
        if self._loop_task and not self._loop_task.done():
            return
        loop = asyncio.get_running_loop()
        self._loop_task = loop.create_task(self._runner(), name="scheduler-dispatcher")

    async def enqueue(self, requests: List[DispatchRequest]) -> None:
        if not requests:
            return
        self.ensure_started()
        for request in requests:
            await self._queue.put(request)

    async def cancel_run(self, run_id: str) -> None:
        # Flush queued dispatches for this run
        if not self._queue.empty():
            retained: List[DispatchRequest] = []
            while not self._queue.empty():
                request = await self._queue.get()
                if request.run_id != run_id:
                    retained.append(request)
                self._queue.task_done()
            for request in retained:
                await self._queue.put(request)

        # Cancel pending ack waiters for this run to avoid retries/timeouts
        async with self._ack_lock:
            for dispatch_id, request in list(self._pending_acks.items()):
                if request.run_id != run_id:
                    continue
                self._pending_acks.pop(dispatch_id, None)
                waiter = self._ack_waiters.pop(dispatch_id, None)
                if waiter:
                    waiter.cancel()

    async def register_ack(self, dispatch_id: str) -> None:
        async with self._ack_lock:
            waiter = self._ack_waiters.pop(dispatch_id, None)
            request = self._pending_acks.pop(dispatch_id, None)
        if waiter:
            waiter.cancel()
            await asyncio.gather(waiter, return_exceptions=True)
        if not request:
            LOGGER.debug("Ack received for unknown dispatch_id=%s", dispatch_id)
            return

        request.dispatch_id = None
        request.ack_deadline = None
        try:
            await run_registry.mark_acknowledged(
                request.run_id,
                node_id=request.node_id,
                dispatch_id=dispatch_id,
            )
        except Exception:  # noqa: BLE001
            LOGGER.exception(
                "Failed to mark dispatch acknowledged run=%s node=%s dispatch=%s",
                request.run_id,
                request.node_id,
                dispatch_id,
            )

    async def _runner(self) -> None:
        while True:
            request = await self._queue.get()
            try:
                await self._dispatch(request)
            except Exception:  # noqa: BLE001
                LOGGER.exception(
                    "Dispatch loop encountered an unexpected error (run=%s node=%s)",
                    request.run_id,
                    request.node_id,
                )
                await self._handle_retry(request, "internal error")
            finally:
                self._queue.task_done()

    async def _dispatch(self, request: DispatchRequest) -> None:
        record = await run_registry.get(request.run_id)
        if not record or record.status in FINAL_STATUSES:
            LOGGER.info(
                "Skipping dispatch for run=%s node=%s (status=%s)",
                request.run_id,
                request.node_id,
                record.status if record else "missing",
            )
            return

        session = self._select_worker(request)
        if not session:
            LOGGER.info(
                "Dispatch pending: no worker available run=%s node=%s attempts=%s",
                request.run_id,
                request.node_id,
                request.attempts,
            )
            await self._handle_retry(request, "worker unavailable")
            return

        try:
            payload = self._build_payload(request)
        except ValueError as exc:
            LOGGER.error(
                "Dropping dispatch for run=%s node=%s due to invalid metadata: %s",
                request.run_id,
                request.node_id,
                exc,
            )
            error_payload = ErrorPayload(
                code="E.DISPATCH.INVALID_METADATA",
                message=str(exc),
                context={
                    "where": "scheduler.dispatch",
                    "details": {
                        "run_id": request.run_id,
                        "node_id": request.node_id,
                        "task_id": request.task_id,
                    },
                },
            )
            await run_registry.record_command_error(
                error_payload,
                run_id=request.run_id,
                task_id=request.task_id,
            )
            return
        try:
            dispatch_id = await worker_manager.dispatch_command(
                session,
                payload,
                tenant=request.tenant,
                corr=request.task_id,
                seq=request.seq,
            )
        except Exception as exc:  # noqa: BLE001
            LOGGER.warning(
                "Dispatch failed run=%s node=%s worker=%s error=%s",
                request.run_id,
                request.node_id,
                session.worker_id,
                exc,
            )
            await self._handle_retry(request, str(exc))
            return

        ack_deadline = datetime.now(timezone.utc) + timedelta(seconds=self._ack_timeout_seconds)
        record = await run_registry.mark_dispatched(
            request.run_id,
            worker_id=session.worker_id,
            task_id=request.task_id,
            node_id=request.node_id,
            node_type=request.node_type,
            package_name=request.package_name,
            package_version=request.package_version,
            seq_used=request.seq,
            resource_refs=request.resource_refs,
            affinity=request.affinity,
            dispatch_id=dispatch_id,
            ack_deadline=ack_deadline,
        )
        if not record or record.status in FINAL_STATUSES:
            LOGGER.info("Dropping dispatch for run=%s node=%s (status=%s)", request.run_id, request.node_id, record.status if record else "unknown")
            return

        async with self._ack_lock:
            request.dispatch_id = dispatch_id
            request.ack_deadline = ack_deadline
            self._pending_acks[dispatch_id] = request
            waiter = asyncio.create_task(
                self._await_ack(dispatch_id),
                name=f"scheduler-dispatcher-ack-{dispatch_id}",
            )
            self._ack_waiters[dispatch_id] = waiter

        request.attempts = 0
        LOGGER.info(
            "Dispatched run=%s node=%s worker=%s dispatch_id=%s",
            request.run_id,
            request.node_id,
            session.worker_id,
            dispatch_id,
        )

    async def _await_ack(self, dispatch_id: str) -> None:
        try:
            await asyncio.sleep(self._ack_timeout_seconds)
        except asyncio.CancelledError:
            return

        async with self._ack_lock:
            request = self._pending_acks.pop(dispatch_id, None)
            self._ack_waiters.pop(dispatch_id, None)

        if not request:
            return

        LOGGER.warning(
            "Dispatch ack timeout run=%s node=%s dispatch_id=%s",
            request.run_id,
            request.node_id,
            dispatch_id,
        )

        try:
            await run_registry.reset_after_ack_timeout(
                request.run_id,
                node_id=request.node_id,
                dispatch_id=dispatch_id,
            )
        except Exception:  # noqa: BLE001
            LOGGER.exception(
                "Failed to reset node state after ack timeout run=%s node=%s dispatch_id=%s",
                request.run_id,
                request.node_id,
                dispatch_id,
            )

        request.dispatch_id = None
        request.ack_deadline = None
        await self._handle_retry(request, "ack timeout")

    def _select_worker(self, request: DispatchRequest) -> Optional[WorkerSession]:
        if request.preferred_worker_id:
            session = worker_manager.get_session(request.preferred_worker_id)
            if not session or session.tenant != request.tenant:
                return None
            if not self._worker_supports_package(session, request.package_name, request.package_version):
                return None
            return session
        return worker_manager.select_session(
            tenant=request.tenant,
            package_name=request.package_name,
            package_version=request.package_version,
        )

    @staticmethod
    def _worker_supports_package(session: WorkerSession, package_name: str, package_version: str) -> bool:
        packages = session.packages or []
        return any(pkg.name == package_name and pkg.version == package_version for pkg in packages)

    @staticmethod
    def _validate_middleware_metadata(request: DispatchRequest) -> None:
        """Ensure middleware chain metadata is self-consistent before dispatch."""

        chain = request.middleware_chain or []
        if not chain:
            # host or non-middleware node without chain
            return
        if not request.host_node_id:
            raise ValueError("middleware_chain present but host_node_id missing")
        # middleware nodes must carry chain_index and match chain entry
        if request.node_id != request.host_node_id:
            if request.chain_index is None:
                raise ValueError("middleware dispatch missing chain_index")
            if request.chain_index < 0 or request.chain_index >= len(chain):
                raise ValueError("middleware chain_index out of bounds")
            if chain[request.chain_index] != request.node_id:
                raise ValueError("middleware chain_index does not match chain entry")
        else:
            # host dispatch should not include chain_index
            if request.chain_index is not None:
                raise ValueError("host dispatch must not include chain_index when middleware_chain is present")

    def _build_payload(self, request: DispatchRequest) -> CommandDispatchPayload:
        resource_refs = [ResourceRef(**ref) for ref in request.resource_refs]
        affinity = Affinity(**request.affinity) if request.affinity else None
        constraints = Constraints()

        # sanity check middleware metadata before payload construction
        try:
            self._validate_middleware_metadata(request)
        except ValueError as exc:
            LOGGER.error(
                "Invalid middleware metadata for dispatch run=%s node=%s: %s",
                request.run_id,
                request.node_id,
                exc,
            )
            raise

        return CommandDispatchPayload(
            run_id=request.run_id,
            task_id=request.task_id,
            node_id=request.node_id,
            node_type=request.node_type,
            package_name=request.package_name,
            package_version=request.package_version,
            parameters=request.parameters,
            host_node_id=request.host_node_id,
            middleware_chain=request.middleware_chain,
            chain_index=request.chain_index,
            constraints=constraints,
            concurrency_key=request.concurrency_key,
            resource_refs=resource_refs or None,
            affinity=affinity,
        )

    async def _handle_retry(self, request: DispatchRequest, message: str) -> None:
        record = await run_registry.get(request.run_id)
        if not record or record.status in FINAL_STATUSES:
            LOGGER.info(
                "Skip retry for run=%s node=%s (status=%s) reason=%s",
                request.run_id,
                request.node_id,
                record.status if record else "missing",
                message,
            )
            return

        request.attempts += 1
        if request.attempts > self._max_attempts:
            LOGGER.error(
                "Dispatch giving up run=%s node=%s reason=%s",
                request.run_id,
                request.node_id,
                message,
            )
            error_payload = ErrorPayload(
                code="E.DISPATCH.UNAVAILABLE",
                message=message,
                context={
                    "where": "scheduler.dispatch",
                    "details": {
                        "run_id": request.run_id,
                        "node_id": request.node_id,
                        "worker": request.preferred_worker_id,
                    },
                },
            )
            await run_registry.record_command_error(
                error_payload,
                run_id=request.run_id,
                task_id=request.task_id,
            )
            return

        delay = min(self._base_retry_seconds * (2 ** (request.attempts - 1)), self._max_retry_seconds)
        await asyncio.sleep(delay)
        await self._queue.put(request)


run_orchestrator = RunOrchestrator()
