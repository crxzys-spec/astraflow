"""Dispatch command handling (biz.exec.dispatch)."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional, Callable, Awaitable, List

from pydantic import ValidationError

from shared.models.biz.exec.dispatch import ExecDispatchPayload
from shared.models.biz.exec.error import ExecErrorPayload
from shared.models.biz.exec.result import Artifact, ExecResultPayload, Status as ResultStatus
from shared.models.session import WsEnvelope

from worker.agent.concurrency import ConcurrencyGuard
from worker.agent.resource_registry import ResourceHandle, ResourceRegistry
from worker.agent.runner import Runner
from worker.config import WorkerSettings
from worker.biz_handlers.next_handler import NextHandler, MiddlewareNextError

LOGGER = logging.getLogger(__name__)


class ResourceLeaseError(RuntimeError):
    """Raised when required resources cannot be leased from the registry."""


@dataclass
class DispatchHandler:
    settings: WorkerSettings
    send_biz: Callable[..., Awaitable[None]]
    next_handler: NextHandler
    concurrency_guard: ConcurrencyGuard
    runner: Optional[Runner] = None
    resource_registry: Optional[ResourceRegistry] = None

    _dispatch_tasks: set[asyncio.Task[None]] = field(default_factory=set, init=False, repr=False)

    async def handle(self, envelope: WsEnvelope) -> None:
        LOGGER.info("Received dispatch command corr=%s", envelope.corr)
        task = asyncio.create_task(self._process_dispatch(envelope), name=f"dispatch-{envelope.id}")
        self._dispatch_tasks.add(task)

        def _finalise(completed: asyncio.Task[None]) -> None:
            self._dispatch_tasks.discard(completed)
            with contextlib.suppress(asyncio.CancelledError, Exception):
                completed.result()

        task.add_done_callback(_finalise)

    async def _process_dispatch(self, envelope: WsEnvelope) -> None:
        try:
            if not self.runner:
                LOGGER.debug("Runner not configured")
                return
            dispatch = ExecDispatchPayload.model_validate(envelope.payload)
            await self._default_command_handler(envelope, dispatch)
        except asyncio.CancelledError:
            LOGGER.debug("Dispatch task %s cancelled", envelope.id)
            raise
        except Exception as exc:  # noqa: BLE001
            LOGGER.exception("Dispatch handling failed for envelope %s: %s", envelope.id, exc)
            raise

    async def _default_command_handler(
        self,
        envelope: WsEnvelope,
        dispatch: ExecDispatchPayload,
    ) -> None:
        if not self.runner:
            LOGGER.error("Runner not configured; cannot execute command")
            return
        corr = envelope.id
        seq = envelope.seq
        try:
            context = self._build_execution_context(dispatch)
            handler_key = dispatch.node_type
            concurrency_key = dispatch.concurrency_key or ""
            async with self.concurrency_guard.acquire(concurrency_key) as acquired:
                if not acquired:
                    LOGGER.warning("Concurrency key %s already in-flight; rejecting task", concurrency_key)
                    await self._send_command_error(
                        ExecErrorPayload(
                            code="E.CMD.CONCURRENCY_VIOLATION",
                            message=f"Concurrency key {concurrency_key} already running",
                            context={
                                "where": "worker.concurrency",
                                "details": {
                                    "run_id": dispatch.run_id,
                                    "task_id": dispatch.task_id,
                                    "node_id": dispatch.node_id,
                                },
                            },
                        ),
                        corr=corr,
                        seq=seq,
                    )
                    return
                leased_resources: dict[str, ResourceHandle] = {}
                try:
                    if self.resource_registry:
                        try:
                            leased_resources = self._lease_resources(dispatch)
                        except ResourceLeaseError as exc:
                            LOGGER.warning("Resource lease failed: %s", exc)
                            await self._send_command_error(
                                ExecErrorPayload(
                                    code="E.RESOURCE.MISSING",
                                    message=str(exc),
                                    context={
                                        "where": "worker.resources",
                                        "details": {
                                            "run_id": dispatch.run_id,
                                            "task_id": dispatch.task_id,
                                            "node_id": dispatch.node_id,
                                        },
                                    },
                                ),
                                corr=corr,
                                seq=seq,
                            )
                            return
                        context.leased_resources = leased_resources
                        context.resource_registry = self.resource_registry
                    start = asyncio.get_event_loop().time()
                    result = await self.runner.execute(context, handler_key, corr=corr, seq=seq)
                    duration_ms = int((asyncio.get_event_loop().time() - start) * 1000)
                    artifacts = self._coerce_artifacts(result.artifacts)
                    metadata_payload: dict[str, Any] = {}
                    if context.metadata:
                        metadata_payload.update(context.metadata)
                    if result.metadata:
                        metadata_payload.update(result.metadata)
                    if not metadata_payload:
                        metadata_payload = {}
                    result_payload = ExecResultPayload(
                        run_id=context.run_id,
                        task_id=context.task_id,
                        status=self._normalise_result_status(result.status),
                        result=result.outputs,
                        duration_ms=duration_ms,
                        metadata=metadata_payload or None,
                        artifacts=artifacts,
                    )
                    await self._send_result(result_payload, corr=corr, seq=seq)
                finally:
                    if self.resource_registry:
                        for resource_id in leased_resources:
                            self.resource_registry.release(resource_id)
        except asyncio.CancelledError:
            current = asyncio.current_task()
            LOGGER.warning(
                "Task cancelled run=%s task=%s node=%s corr=%s seq=%s current_task=%s",
                dispatch.run_id,
                dispatch.task_id,
                dispatch.node_id,
                corr,
                seq,
                getattr(current, "get_name", lambda: None)(),
            )
            try:
                await self.next_handler.interrupt_pending_next(
                    dispatch.run_id, dispatch.task_id, code="next_cancelled", message="task cancelled"
                )
                await self._send_command_error(
                    ExecErrorPayload(
                        code="E.RUNNER.CANCELLED",
                        message="task cancelled",
                        context={
                            "where": "worker.runner",
                            "details": {
                                "run_id": dispatch.run_id,
                                "task_id": dispatch.task_id,
                                "node_id": dispatch.node_id,
                            },
                        },
                    ),
                    corr=corr,
                    seq=seq,
                )
            finally:
                raise
        except Exception as exc:  # noqa: BLE001
            LOGGER.exception("Command execution failed: %s", exc)
            await self._send_command_error(
                ExecErrorPayload(
                    code="E.RUNNER.FAILURE",
                    message=str(exc),
                    context={
                        "where": "worker.runner",
                        "details": {
                            "run_id": dispatch.run_id,
                            "task_id": dispatch.task_id,
                            "node_id": dispatch.node_id,
                        },
                    },
                ),
                corr=corr,
                seq=seq,
            )
        finally:
            self.next_handler.cancel_pending_next_for_task(dispatch.run_id, dispatch.task_id)

    def _coerce_artifacts(self, artifacts: Optional[List[Any]]) -> Optional[List[Artifact]]:
        if not artifacts:
            return None
        coerced: List[Artifact] = []
        for entry in artifacts:
            if isinstance(entry, Artifact):
                coerced.append(entry)
                continue
            try:
                coerced.append(Artifact.model_validate(entry))
            except ValidationError as exc:  # noqa: BLE001
                LOGGER.warning("Dropping invalid artifact descriptor %s: %s", entry, exc)
        return coerced or None

    def _build_execution_context(self, dispatch: ExecDispatchPayload) -> "ExecutionContext":
        from worker.agent.runner import ExecutionContext  # local import to avoid cycles
        from worker.agent.feedback import FeedbackPublisher

        run_id = dispatch.run_id
        task_id = dispatch.task_id
        node_id = dispatch.node_id
        package_name = dispatch.package_name
        package_version = dispatch.package_version
        parameters = dispatch.parameters or {}
        safe_task_id = self._sanitize_path_segment(task_id)
        data_dir = Path(self.settings.data_dir) / run_id / safe_task_id
        data_dir.mkdir(parents=True, exist_ok=True)
        trace = None
        metadata = {
            "concurrency_key": dispatch.concurrency_key,
            "constraints": dispatch.constraints.model_dump(exclude_none=True),
        }
        if dispatch.host_node_id:
            metadata["host_node_id"] = dispatch.host_node_id
        if dispatch.middleware_chain:
            metadata["middleware_chain"] = list(dispatch.middleware_chain)
        if dispatch.chain_index is not None:
            metadata["chain_index"] = dispatch.chain_index
        resource_refs = list(dispatch.resource_refs) if dispatch.resource_refs else None
        if resource_refs:
            metadata["resource_refs"] = [ref.model_dump(exclude_none=True) for ref in resource_refs]
        if dispatch.affinity:
            metadata["affinity"] = dispatch.affinity.model_dump(exclude_none=True)
        context = ExecutionContext(
            run_id=run_id,
            task_id=task_id,
            node_id=node_id,
            package_name=package_name,
            package_version=package_version,
            params=parameters,
            data_dir=data_dir,
            tenant=self.settings.tenant,
            host_node_id=dispatch.host_node_id,
            middleware_chain=dispatch.middleware_chain,
            chain_index=dispatch.chain_index,
            trace=trace,
            metadata=metadata,
            resource_refs=resource_refs,
            resource_registry=self.resource_registry,
            feedback=FeedbackPublisher(self, run_id=run_id, task_id=task_id),
        )
        context.next_handler = self.next_handler.middleware_next
        return context

    @staticmethod
    def _sanitize_path_segment(segment: str) -> str:
        cleaned = re.sub(r'[<>:"/\\\\|?*]', "_", segment)
        cleaned = cleaned.strip(". ")
        return cleaned or "task"

    def _normalise_result_status(self, status: str) -> ResultStatus:
        if not status:
            LOGGER.warning("Adapter returned empty status; defaulting to FAILED")
            return ResultStatus.FAILED
        upper = status.upper()
        mapping = {
            "SUCCESS": ResultStatus.SUCCEEDED.value,
            "SUCCEED": ResultStatus.SUCCEEDED.value,
            "SUCCEEDED": ResultStatus.SUCCEEDED.value,
            "ALLOWED": ResultStatus.SUCCEEDED.value,
            "BLOCKED": ResultStatus.SUCCEEDED.value,
            "OK": ResultStatus.SUCCEEDED.value,
            "DONE": ResultStatus.SUCCEEDED.value,
            "ERROR": ResultStatus.FAILED.value,
            "FAIL": ResultStatus.FAILED.value,
            "FAILED": ResultStatus.FAILED.value,
            "CANCEL": ResultStatus.CANCELLED.value,
            "CANCELLED": ResultStatus.CANCELLED.value,
            "SKIP": ResultStatus.SKIPPED.value,
            "SKIPPED": ResultStatus.SKIPPED.value,
        }
        canonical = mapping.get(upper, upper)
        try:
            return ResultStatus(canonical)
        except ValueError:
            LOGGER.warning("Adapter returned unsupported status '%s'; defaulting to FAILED", status)
        return ResultStatus.FAILED

    def _lease_resources(self, dispatch: ExecDispatchPayload) -> dict[str, ResourceHandle]:
        leased: dict[str, ResourceHandle] = {}
        if not self.resource_registry or not dispatch.resource_refs:
            return leased
        for ref in dispatch.resource_refs:
            if ref.worker_name and ref.worker_name != self.settings.worker_name:
                raise ResourceLeaseError(
                    f"resource {ref.resource_id} pinned to {ref.worker_name}, current worker {self.settings.worker_name}"
                )
            try:
                handle = self.resource_registry.lease(ref.resource_id)
            except KeyError as exc:
                raise ResourceLeaseError(f"resource {ref.resource_id} missing on worker") from exc
            leased[ref.resource_id] = handle
        return leased

    async def cancel_dispatch_tasks(self) -> None:
        if not self._dispatch_tasks:
            return
        tasks = list(self._dispatch_tasks)
        self._dispatch_tasks.clear()
        LOGGER.debug("Cancelling %s dispatch tasks", len(tasks))
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

    # Outbound send helpers -------------------------------------------------
    async def send_feedback(self, payload: Any, *, corr: Optional[str] = None, seq: Optional[int] = None) -> None:
        await self.send_biz("biz.exec.feedback", payload, corr=corr, seq=seq)

    async def _send_command_error(
        self,
        payload: ExecErrorPayload,
        *,
        corr: Optional[str] = None,
        seq: Optional[int] = None,
    ) -> None:
        await self.send_biz("biz.exec.error", payload, require_ack=True, corr=corr, seq=seq)

    async def _send_result(
        self,
        payload: ExecResultPayload,
        *,
        corr: Optional[str] = None,
        seq: Optional[int] = None,
    ) -> None:
        await self.send_biz("biz.exec.result", payload, require_ack=True, corr=corr, seq=seq)
