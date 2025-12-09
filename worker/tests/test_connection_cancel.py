import asyncio
import logging
from datetime import datetime, timezone

import pytest

from shared.models.ws.cmd.dispatch import CommandDispatchPayload, Constraints
from shared.models.ws.envelope import Role, Sender, WsEnvelope
from shared.models.ws.next import NextResponsePayload
from worker.agent.config import WorkerSettings
from worker.agent.connection import ControlPlaneConnection, DummyTransport


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

    conn = ControlPlaneConnection(
        settings=settings,
        transport_factory=lambda _: transport,
        runner=_CancelRunner(),
    )

    dispatched_errors = []

    async def _fake_send_error(payload, *, corr=None, seq=None):
        dispatched_errors.append(payload)

    monkeypatch.setattr(conn, "send_command_error", _fake_send_error)

    dispatch = CommandDispatchPayload(
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
        type="cmd.dispatch",
        id="env-1",
        ts=datetime.now(timezone.utc),
        corr="task-1",
        seq=1,
        tenant=settings.tenant,
        sender=Sender(role=Role.scheduler, id="scheduler-1"),
        payload=dispatch.model_dump(by_alias=True),
    )

    with pytest.raises(asyncio.CancelledError):
        await conn._default_command_handler(envelope, dispatch)

    assert dispatched_errors, "Cancellation should emit command.error"
    assert dispatched_errors[0].code == "E.RUNNER.CANCELLED"


@pytest.mark.asyncio
async def test_late_next_response_after_local_cancel_is_ignored(caplog):
    settings = WorkerSettings()
    transport = DummyTransport(settings)
    conn = ControlPlaneConnection(
        settings=settings,
        transport_factory=lambda _: transport,
    )

    request_id = "req-cancelled"
    fut = asyncio.get_running_loop().create_future()
    async with conn._next_lock:
        conn._pending_next[request_id] = (fut, "task-cancelled")

    caplog.set_level(logging.DEBUG, logger="worker.agent.connection")

    await conn._interrupt_pending_next("task-cancelled", code="next_cancelled", message="task cancelled")

    payload = NextResponsePayload(
        requestId=request_id,
        runId="run-ignored",
        nodeId="node-1",
        middlewareId="mw-1",
        result={"ok": True},
    )
    envelope = WsEnvelope(
        type="middleware.next_response",
        id="env-next",
        ts=datetime.now(timezone.utc),
        corr=request_id,
        seq=None,
        tenant=settings.tenant,
        sender=Sender(role=Role.scheduler, id="scheduler-1"),
        payload=payload.model_dump(by_alias=True, exclude_none=True),
    )

    await conn._handle_next_response(envelope)

    warnings = [record for record in caplog.records if record.levelno >= logging.WARNING]
    assert not warnings, "Late next responses for cancelled waits should be ignored without warnings"
    assert request_id not in conn._aborted_next_index
