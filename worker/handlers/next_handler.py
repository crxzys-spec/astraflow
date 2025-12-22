"""Middleware next request/response handling."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Callable, Awaitable

from shared.models.biz.exec.next.request import ExecMiddlewareNextRequest
from shared.models.biz.exec.next.response import ExecMiddlewareNextResponse
from shared.models.session import WsEnvelope

LOGGER = logging.getLogger(__name__)

_ABORTED_NEXT_MAX = 512


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
class NextHandler:
    send_biz: Callable[..., Awaitable[None]]
    next_message_id: Callable[[str], str]

    _pending_next: Dict[str, tuple[asyncio.Future, str, str]] = field(default_factory=dict)
    _next_lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    _aborted_next: list[str] = field(default_factory=list)
    _aborted_next_index: set[str] = field(default_factory=set)

    async def middleware_next(
        self,
        context: Any,
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
            await self.send_biz("biz.exec.next.request", next_payload, require_ack=True, corr=context.task_id)
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
            fut, *_ = self._pending_next.pop(req_id, (None, task_id, run_id))
            if fut and not fut.done():
                fut.cancel()
            self._track_aborted_next(req_id)

    def _track_aborted_next(self, request_id: str) -> None:
        if request_id in self._aborted_next_index:
            return
        self._aborted_next.append(request_id)
        self._aborted_next_index.add(request_id)
        if len(self._aborted_next) > _ABORTED_NEXT_MAX:
            oldest = self._aborted_next.pop(0)
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
