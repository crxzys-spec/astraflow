"""Dispatch execution pipeline for worker nodes."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Optional, Protocol

from shared.models.biz.exec.dispatch import ExecDispatchPayload
from shared.models.biz.exec.error import ExecErrorPayload
from shared.models.biz.exec.result import ExecResultPayload

from worker.execution.runtime import ConcurrencyGuard, ResourceHandle, ResourceRegistry
from worker.config import WorkerSettings

from .context import ExecutionContextFactory, FeedbackSender
from .results import ExecutionResultBuilder

LOGGER = logging.getLogger(__name__)


class RunnerLike(Protocol):
    async def execute(self, context, handler_key, *, corr: Optional[str] = None, seq: Optional[int] = None): ...


class ResourceLeaseError(RuntimeError):
    """Raised when required resources cannot be leased from the registry."""


@dataclass
class DispatchOutcome:
    result: Optional[ExecResultPayload] = None
    error: Optional[ExecErrorPayload] = None


def build_exec_error(
    dispatch: ExecDispatchPayload,
    *,
    code: str,
    message: str,
    where: str,
) -> ExecErrorPayload:
    return ExecErrorPayload(
        code=code,
        message=message,
        context={
            "where": where,
            "details": {
                "run_id": dispatch.run_id,
                "task_id": dispatch.task_id,
                "node_id": dispatch.node_id,
            },
        },
    )


@dataclass
class DispatchExecutor:
    settings: WorkerSettings
    concurrency_guard: ConcurrencyGuard
    runner: RunnerLike
    context_factory: ExecutionContextFactory
    result_builder: ExecutionResultBuilder
    resource_registry: Optional[ResourceRegistry] = None

    async def execute(
        self,
        dispatch: ExecDispatchPayload,
        *,
        corr: Optional[str] = None,
        seq: Optional[int] = None,
        feedback_sender: FeedbackSender,
    ) -> DispatchOutcome:
        context = self.context_factory.build(dispatch, feedback_sender=feedback_sender)
        handler_key = dispatch.node_type
        concurrency_key = dispatch.concurrency_key or ""
        leased_resources: dict[str, ResourceHandle] = {}
        async with self.concurrency_guard.acquire(concurrency_key) as acquired:
            if not acquired:
                LOGGER.warning("Concurrency key %s already in-flight; rejecting task", concurrency_key)
                return DispatchOutcome(
                    error=build_exec_error(
                        dispatch,
                        code="E.CMD.CONCURRENCY_VIOLATION",
                        message=f"Concurrency key {concurrency_key} already running",
                        where="worker.concurrency",
                    )
                )
            try:
                if self.resource_registry:
                    leased_resources = self._lease_resources(dispatch)
                    context.leased_resources = leased_resources
                loop = asyncio.get_running_loop()
                start = loop.time()
                result = await self.runner.execute(context, handler_key, corr=corr, seq=seq)
                duration_ms = int((loop.time() - start) * 1000)
                return DispatchOutcome(
                    result=self.result_builder.build(context, result, duration_ms=duration_ms),
                )
            except asyncio.CancelledError:
                raise
            except ResourceLeaseError as exc:
                LOGGER.warning("Resource lease failed: %s", exc)
                return DispatchOutcome(
                    error=build_exec_error(
                        dispatch,
                        code="E.RESOURCE.MISSING",
                        message=str(exc),
                        where="worker.resources",
                    )
                )
            except Exception as exc:  # noqa: BLE001
                LOGGER.exception("Command execution failed: %s", exc)
                return DispatchOutcome(
                    error=build_exec_error(
                        dispatch,
                        code="E.RUNNER.FAILURE",
                        message=str(exc),
                        where="worker.runner",
                    )
                )
            finally:
                if self.resource_registry:
                    for resource_id in leased_resources:
                        self.resource_registry.release(resource_id)

    def _lease_resources(self, dispatch: ExecDispatchPayload) -> dict[str, ResourceHandle]:
        leased: dict[str, ResourceHandle] = {}
        if not self.resource_registry or not dispatch.resource_refs:
            return leased
        for ref in dispatch.resource_refs:
            if ref.worker_name and ref.worker_name != self.settings.worker_name:
                self._release_leased(leased)
                raise ResourceLeaseError(
                    f"resource {ref.resource_id} pinned to {ref.worker_name}, current worker {self.settings.worker_name}"
                )
            try:
                handle = self.resource_registry.lease(ref.resource_id)
            except KeyError as exc:
                self._release_leased(leased)
                raise ResourceLeaseError(f"resource {ref.resource_id} missing on worker") from exc
            leased[ref.resource_id] = handle
        return leased

    def _release_leased(self, leased: dict[str, ResourceHandle]) -> None:
        if not self.resource_registry:
            return
        for resource_id in leased:
            self.resource_registry.release(resource_id)
