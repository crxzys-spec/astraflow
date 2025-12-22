"""Dispatch command handling (biz.exec.dispatch)."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Optional

from shared.models.biz.exec.dispatch import ExecDispatchPayload
from shared.models.biz.exec.error import ExecErrorPayload
from shared.models.biz.exec.result import ExecResultPayload
from shared.models.session import WsEnvelope

from worker.execution.runtime import ConcurrencyGuard
from worker.execution import (
    DispatchExecutor,
    ExecutionContextFactory,
    ExecutionResultBuilder,
    build_exec_error,
)
from worker.execution.runtime import ResourceRegistry
from worker.execution import Runner
from worker.handlers.next_handler import NextHandler
from worker.config import WorkerSettings

LOGGER = logging.getLogger(__name__)


@dataclass
class DispatchHandler:
    settings: WorkerSettings
    send_biz: Callable[..., Awaitable[None]]
    next_handler: NextHandler
    concurrency_guard: ConcurrencyGuard
    runner: Optional[Runner] = None
    resource_registry: Optional[ResourceRegistry] = None

    _dispatch_tasks: set[asyncio.Task[None]] = field(default_factory=set, init=False, repr=False)
    _executor: Optional[DispatchExecutor] = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        self._executor = self._build_executor()

    def _build_executor(self) -> DispatchExecutor:
        return DispatchExecutor(
            settings=self.settings,
            concurrency_guard=self.concurrency_guard,
            runner=self.runner,
            resource_registry=self.resource_registry,
            context_factory=ExecutionContextFactory(
                settings=self.settings,
                next_handler=self.next_handler,
                resource_registry=self.resource_registry,
            ),
            result_builder=ExecutionResultBuilder(),
        )

    def _ensure_executor(self) -> DispatchExecutor:
        if (
            not self._executor
            or self._executor.runner is not self.runner
            or self._executor.resource_registry is not self.resource_registry
        ):
            self._executor = self._build_executor()
        return self._executor

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
            executor = self._ensure_executor()
            outcome = await executor.execute(dispatch, corr=corr, seq=seq, feedback_sender=self)
            if outcome.error:
                await self._send_command_error(outcome.error, corr=corr, seq=seq)
                return
            if outcome.result:
                await self._send_result(outcome.result, corr=corr, seq=seq)
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
                    build_exec_error(
                        dispatch,
                        code="E.RUNNER.CANCELLED",
                        message="task cancelled",
                        where="worker.runner",
                    ),
                    corr=corr,
                    seq=seq,
                )
            finally:
                raise
        except Exception as exc:  # noqa: BLE001
            LOGGER.exception("Command execution failed: %s", exc)
            await self._send_command_error(
                build_exec_error(
                    dispatch,
                    code="E.RUNNER.FAILURE",
                    message=str(exc),
                    where="worker.runner",
                ),
                corr=corr,
                seq=seq,
            )
        finally:
            self.next_handler.cancel_pending_next_for_task(dispatch.run_id, dispatch.task_id)

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
