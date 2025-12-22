import asyncio
import logging
from datetime import datetime, timezone

import pytest

from shared.models.biz.exec.dispatch import ExecDispatchPayload, Constraints
from shared.models.biz.exec.next.response import ExecMiddlewareNextResponse
from shared.models.session import Role, Sender, WsEnvelope
from worker.config import WorkerSettings
from worker.network.client import NetworkClient
from worker.network.transport.dummy import DummyTransport
from worker.biz_handlers.dispatch_handler import DispatchHandler
from worker.biz_handlers.next_handler import NextHandler


class _CancelRunner:
    async def execute(self, context, handler_key, *, corr=None, seq=None):
        raise asyncio.CancelledError()


class _SinkTransport(DummyTransport):
    def __init__(self) -> None:
        super().__init__(None)
        self.sent = []

    async def send(self, message: dict[str, object]) -> None:
        self.sent.append(message)


@pytest.mark.asyncio
async def test_default_command_handler_reports_cancel(monkeypatch):
    settings = WorkerSettings()
    transport = _SinkTransport()

    conn = NetworkClient(
        settings=settings,
        transport_factory=lambda _: transport,
        runner=_CancelRunner(),
    )

    dispatched_errors = []

    conn._ensure_layers()
    next_handler = NextHandler(send_biz=conn.send_biz, next_message_id=conn.next_message_id)
    dispatch_handler = DispatchHandler(
        settings=settings,
        send_biz=conn.send_biz,
        next_handler=next_handler,
        concurrency_guard=conn.concurrency_guard,
        runner=_CancelRunner(),
        resource_registry=None,
    )
    conn.register_handler("biz.exec.dispatch", dispatch_handler.handle)
    conn.register_handler("biz.exec.next.response", next_handler.handle_next_response)

    async def _fake_send_error(payload, *, corr=None, seq=None):
        dispatched_errors.append(payload)

    monkeypatch.setattr(dispatch_handler, "_send_command_error", _fake_send_error)

    dispatch = ExecDispatchPayload(
        run_id="run-1",
        task_id="task-1",
        node_id="node-1",
        node_type="node-type",
        package_name="pkg",
        package_version="1.0.0",
        parameters={},
        constraints=Constraints(),
        concurrency_key="ck",
    )
    envelope = WsEnvelope(
        type="biz.exec.dispatch",
        id="env-1",
        ts=datetime.now(timezone.utc),
        corr="task-1",
        seq=1,
        tenant=settings.tenant,
        sender=Sender(role=Role.scheduler, id="scheduler-1"),
        payload=dispatch.model_dump(by_alias=True),
    )

    with pytest.raises(asyncio.CancelledError):
        await dispatch_handler._default_command_handler(envelope, dispatch)

    assert dispatched_errors, "Cancellation should emit command.error"
    assert dispatched_errors[0].code == "E.RUNNER.CANCELLED"


@pytest.mark.asyncio
async def test_late_next_response_after_local_cancel_is_ignored(caplog):
    settings = WorkerSettings()
    transport = DummyTransport(settings)
    conn = NetworkClient(
        settings=settings,
        transport_factory=lambda _: transport,
    )

    conn._ensure_layers()
    next_handler = NextHandler(send_biz=conn.send_biz, next_message_id=conn.next_message_id)
    dispatch_handler = DispatchHandler(
        settings=settings,
        send_biz=conn.send_biz,
        next_handler=next_handler,
        concurrency_guard=conn.concurrency_guard,
        runner=None,
        resource_registry=None,
    )
    conn.register_handler("biz.exec.dispatch", dispatch_handler.handle)
    conn.register_handler("biz.exec.next.response", next_handler.handle_next_response)

    request_id = "req-cancelled"
    fut = asyncio.get_running_loop().create_future()
    async with next_handler._next_lock:
        next_handler._pending_next[request_id] = (fut, "task-cancelled", "run-cancelled")

    caplog.set_level(logging.DEBUG)

    await next_handler.interrupt_pending_next("run-cancelled", "task-cancelled", code="next_cancelled", message="task cancelled")

    payload = ExecMiddlewareNextResponse(
        requestId=request_id,
        runId="run-ignored",
        nodeId="node-1",
        middlewareId="mw-1",
        result={"ok": True},
    )
    envelope = WsEnvelope(
        type="biz.exec.next.response",
        id="env-next",
        ts=datetime.now(timezone.utc),
        corr=request_id,
        seq=None,
        tenant=settings.tenant,
        sender=Sender(role=Role.scheduler, id="scheduler-1"),
        payload=payload.model_dump(by_alias=True, exclude_none=True),
    )

    await next_handler.handle_next_response(envelope)

    warnings = [record for record in caplog.records if record.levelno >= logging.WARNING]
    assert not warnings, "Late next responses for cancelled waits should be ignored without warnings"
    assert request_id not in next_handler._aborted_next_index
