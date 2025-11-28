import asyncio
from datetime import datetime, timezone

import pytest

from shared.models.ws.cmd.dispatch import CommandDispatchPayload, Constraints
from shared.models.ws.envelope import Role, Sender, WsEnvelope
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
