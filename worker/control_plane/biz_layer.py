"""Business-layer protocol handling (biz.*) for the worker control-plane."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import re
from collections import deque
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional, Set

from pydantic import BaseModel, ValidationError

from shared.models.biz.exec.dispatch import ExecDispatchPayload
from shared.models.biz.exec.error import ExecErrorPayload
from shared.models.biz.exec.feedback import ExecFeedbackPayload
from shared.models.biz.exec.next.request import ExecMiddlewareNextRequest
from shared.models.biz.exec.next.response import ExecMiddlewareNextResponse
from shared.models.biz.exec.result import Artifact, ExecResultPayload, Status as ResultStatus
from shared.models.session import WsEnvelope

from worker.agent.concurrency import ConcurrencyGuard
from worker.agent.resource_registry import ResourceHandle, ResourceRegistry
from worker.agent.runner import Runner
from worker.config import WorkerSettings

LOGGER = logging.getLogger(__name__)

_ABORTED_NEXT_MAX = 512


class ResourceLeaseError(RuntimeError):
    """Raised when required resources cannot be leased from the registry."""


class MiddlewareNextError(RuntimeError):
    """Raised when middleware next invocation returns an error."""

    def __init__(
        self,
        message: str,
        *,
        code: Optional[str] = None,
        trace: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.trace = trace


@dataclass
class BizLayer:
    """Handles business-level frames (biz.*) and drives task execution."""

    settings: WorkerSettings
    build_envelope: Callable[..., dict[str, Any]]
    send: Callable[[dict[str, Any]], Awaitable[None]]
    next_message_id: Callable[[str], str]
    concurrency_guard: ConcurrencyGuard
    runner: Optional[Runner] = None
    command_handler: Optional[Callable[[dict[str, Any]], Awaitable[None]]] = None
    package_handler: Optional[Callable[[str, dict[str, Any]], Awaitable[None]]] = None
    resource_registry: Optional[ResourceRegistry] = None

    _dispatch_tasks: Set[asyncio.Task[None]] = field(default_factory=set)
    _pending_next: Dict[str, tuple[asyncio.Future, str, str]] = field(default_factory=dict)
    _next_lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    _aborted_next: Deque[str] = field(default_factory=deque)
    _aborted_next_index: Set[str] = field(default_factory=set)

    async def handle_envelope(self, envelope: WsEnvelope) -> None:
        message_type = envelope.type
        payload = envelope.payload
        if message_type == "biz.exec.dispatch":
            LOGGER.info("Received dispatch command corr=%s", envelope.corr)
            self._schedule_dispatch(envelope)
        elif message_type == "biz.exec.next.response":
            await self.handle_next_response(envelope)
        elif message_type == "biz.pkg.install":
            LOGGER.info("Received package install instruction: %s", payload)
            if self.package_handler:
                await self.package_handler("install", envelope.model_dump(by_alias=True))
        elif message_type == "biz.pkg.uninstall":
            LOGGER.info("Received package uninstall instruction: %s", payload)
            if self.package_handler:
                await self.package_handler("uninstall", envelope.model_dump(by_alias=True))
        else:
            LOGGER.debug("Unhandled business message type %s", message_type)

    def _schedule_dispatch(self, envelope: WsEnvelope) -> None:
        task = asyncio.create_task(self._process_dispatch(envelope), name=f"dispatch-{envelope.id}")
        self._dispatch_tasks.add(task)

        def _finalise(completed: asyncio.Task[None]) -> None:
            self._dispatch_tasks.discard(completed)
            with contextlib.suppress(asyncio.CancelledError, Exception):
                completed.result()

        task.add_done_callback(_finalise)

    async def _process_dispatch(self, envelope: WsEnvelope) -> None:
        try:
            if self.command_handler:
                await self.command_handler(envelope.model_dump(by_alias=True))
                return
            if not self.runner:
                LOGGER.debug("No command handler registered")
                return
            dispatch = ExecDispatchPayload.model_validate(envelope.payload)
            await self.default_command_handler(envelope, dispatch)
        except asyncio.CancelledError:
            LOGGER.debug("Dispatch task %s cancelled", envelope.id)
            raise
        except Exception as exc:  # noqa: BLE001
            LOGGER.exception("Dispatch handling failed for envelope %s: %s", envelope.id, exc)
            raise

    async def default_command_handler(
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
            context = self.build_execution_context(dispatch)
            handler_key = dispatch.node_type
            concurrency_key = dispatch.concurrency_key or ""
            async with self.concurrency_guard.acquire(concurrency_key) as acquired:
                if not acquired:
                    LOGGER.warning("Concurrency key %s already in-flight; rejecting task", concurrency_key)
                    await self.send_command_error(
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
                            await self.send_command_error(
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
                    await self.send_result(
                        result_payload,
                        corr=corr,
                        seq=seq,
                    )
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
                await self.interrupt_pending_next(
                    dispatch.run_id, dispatch.task_id, code="next_cancelled", message="task cancelled"
                )
                await self.send_command_error(
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
            await self.send_command_error(
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
            self.cancel_pending_next_for_task(dispatch.run_id, dispatch.task_id)

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

    def build_execution_context(self, dispatch: ExecDispatchPayload) -> "ExecutionContext":
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
        context.next_handler = self.middleware_next
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

    async def send_result(self, payload: dict[str, Any] | BaseModel, *, corr: Optional[str] = None, seq: Optional[int] = None) -> None:
        message = self.build_envelope("biz.exec.result", payload, request_ack=True, corr=corr, seq=seq)
        await self.send(message)

    async def send_feedback(
        self,
        payload: ExecFeedbackPayload | dict[str, Any] | BaseModel,
        *,
        corr: Optional[str] = None,
        seq: Optional[int] = None,
    ) -> None:
        message = self.build_envelope("biz.exec.feedback", payload, request_ack=False, corr=corr, seq=seq)
        await self.send(message)

    async def send_command_error(
        self,
        payload: dict[str, Any] | BaseModel,
        *,
        corr: Optional[str] = None,
        seq: Optional[int] = None,
    ) -> None:
        message = self.build_envelope("biz.exec.error", payload, request_ack=True, corr=corr, seq=seq)
        await self.send(message)

    async def send_package_event(self, payload: dict[str, Any] | BaseModel) -> None:
        message = self.build_envelope("biz.pkg.event", payload, request_ack=False)
        await self.send(message)

    def _track_aborted_next(self, request_id: str) -> None:
        if request_id in self._aborted_next_index:
            return
        self._aborted_next.append(request_id)
        self._aborted_next_index.add(request_id)
        if len(self._aborted_next) > _ABORTED_NEXT_MAX:
            oldest = self._aborted_next.popleft()
            self._aborted_next_index.discard(oldest)

    def _pop_aborted_next(self, request_id: str) -> bool:
        if request_id not in self._aborted_next_index:
            return False
        self._aborted_next_index.discard(request_id)
        try:
            self._aborted_next.remove(request_id)
        except ValueError:
            pass
        return True

    def cancel_pending_next(self) -> None:
        if self._pending_next:
            LOGGER.debug("Cancelling %s pending next requests", len(self._pending_next))
        for req_id, (fut, _, _) in list(self._pending_next.items()):
            if not fut.done():
                fut.cancel()
            self._track_aborted_next(req_id)
        self._pending_next.clear()

    def cancel_pending_next_for_task(self, run_id: str, task_id: str) -> None:
        to_cancel = [req_id for req_id, (_, tid, rid) in self._pending_next.items() if tid == task_id and rid == run_id]
        if to_cancel:
            LOGGER.debug("Cancelling %s pending next requests for task=%s", len(to_cancel), task_id)
        for req_id in to_cancel:
            fut, _, _ = self._pending_next.pop(req_id, (None, task_id, run_id))
            if fut and not fut.done():
                fut.cancel()
            self._track_aborted_next(req_id)

    async def interrupt_pending_next(self, run_id: str, task_id: str, *, code: str, message: str) -> None:
        async with self._next_lock:
            targets = [
                (req_id, fut)
                for req_id, (fut, tid, rid) in self._pending_next.items()
                if tid == task_id and rid == run_id
            ]
            if targets:
                LOGGER.debug(
                    "Interrupting %s pending next requests for task=%s with code=%s message=%s",
                    len(targets),
                    task_id,
                    code,
                    message,
                )
            for req_id, fut in targets:
                self._pending_next.pop(req_id, None)
                if fut and not fut.done():
                    fut.set_exception(MiddlewareNextError(message, code=code))
                self._track_aborted_next(req_id)

    async def cancel_dispatch_tasks(self) -> None:
        if not self._dispatch_tasks:
            return
        tasks = list(self._dispatch_tasks)
        self._dispatch_tasks.clear()
        LOGGER.debug("Cancelling %s dispatch tasks", len(tasks))
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

    async def middleware_next(
        self,
        context: "ExecutionContext",
        payload: Optional[Dict[str, Any]],
        host_ctx: Optional[Dict[str, Any]],
        middleware_ctx: Optional[Dict[str, Any]],
        timeout_ms: Optional[int],
    ) -> Dict[str, Any]:
        if not context.middleware_chain or context.chain_index is None:
            raise RuntimeError("middleware chain metadata missing; cannot call next()")
        request_id = self.next_message_id("next")
        timeout_seconds = timeout_ms / 1000.0 if timeout_ms and timeout_ms > 0 else None
        next_payload = ExecMiddlewareNextRequest(
            requestId=request_id,
            runId=context.run_id,
            nodeId=context.node_id,
            middlewareId=context.node_id,
            chainIndex=context.chain_index,
            hostCtx=host_ctx,
            middlewareCtx=middleware_ctx,
            payload=payload,
            timeoutMs=timeout_ms,
        )
        loop = asyncio.get_running_loop()
        future: asyncio.Future = loop.create_future()
        async with self._next_lock:
            self._pending_next[request_id] = (future, context.task_id, context.run_id)
        try:
            message = self.build_envelope(
                "biz.exec.next.request",
                next_payload,
                request_ack=True,
                corr=context.task_id,
                seq=None,
            )
            await self.send(message)
        except Exception:
            async with self._next_lock:
                self._pending_next.pop(request_id, None)
            raise

        try:
            if timeout_seconds:
                return await asyncio.wait_for(future, timeout=timeout_seconds)
            return await future
        except asyncio.TimeoutError as exc:
            future.cancel()
            self._track_aborted_next(request_id)
            raise MiddlewareNextError(
                "middleware next timed out locally",
                code="next_timeout",
            ) from exc
        except asyncio.CancelledError:
            future.cancel()
            self._track_aborted_next(request_id)
            raise
        finally:
            async with self._next_lock:
                self._pending_next.pop(request_id, None)

    async def handle_next_response(self, envelope: WsEnvelope) -> None:
        payload = ExecMiddlewareNextResponse.model_validate(envelope.payload)
        request_id = payload.requestId
        async with self._next_lock:
            entry = self._pending_next.pop(request_id, None)
        if not entry:
            if self._pop_aborted_next(request_id):
                LOGGER.debug(
                    "Ignored late middleware.next_response for aborted waiter req=%s run=%s",
                    request_id,
                    payload.runId,
                )
            else:
                LOGGER.warning(
                    "Received middleware.next_response with no pending waiter req=%s run=%s",
                    request_id,
                    payload.runId,
                )
            return
        future, *_ = entry
        if future.done():
            return
        if payload.error:
            code = payload.error.get("code") if isinstance(payload.error, dict) else None
            message = payload.error.get("message") if isinstance(payload.error, dict) else "middleware next failed"
            future.set_exception(MiddlewareNextError(message, code=code, trace=payload.trace))
            return
        future.set_result(payload.result or {})
