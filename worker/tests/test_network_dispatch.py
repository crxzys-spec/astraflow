import asyncio
from datetime import datetime, timezone

import pytest

from shared.models.session import Role, Sender, WsEnvelope
from worker.config import WorkerSettings
from worker.network.client import NetworkClient
from worker.network.transport.dummy import DummyTransport


def _make_envelope(settings: WorkerSettings, message_type: str, envelope_id: str) -> WsEnvelope:
    return WsEnvelope(
        type=message_type,
        id=envelope_id,
        ts=datetime.now(timezone.utc),
        corr=None,
        seq=None,
        tenant=settings.tenant,
        sender=Sender(role=Role.scheduler, id="scheduler-1"),
        payload={},
    )


@pytest.mark.asyncio
async def test_dispatch_queue_drop_oldest():
    settings = WorkerSettings(
        dispatch_queue_max=1,
        dispatch_queue_overflow="drop_oldest",
        dispatch_max_inflight=0,
    )
    client = NetworkClient(
        settings=settings,
        transport_factory=lambda _: DummyTransport(settings),
    )
    client._ensure_dispatch_control()

    queue = asyncio.Queue(maxsize=1)
    first = _make_envelope(settings, "biz.test", "env-1")
    second = _make_envelope(settings, "biz.test", "env-2")
    await queue.put(first)
    client._type_queues["biz.test"] = queue

    await client._enqueue_type("biz.test", second)

    assert queue.qsize() == 1
    item = await queue.get()
    assert item.id == "env-2"


@pytest.mark.asyncio
async def test_handler_timeout_enters_cooldown():
    settings = WorkerSettings(
        dispatch_timeout_seconds=0.01,
        dispatch_max_failures=1,
        dispatch_failure_cooldown_seconds=0.1,
        dispatch_max_inflight=0,
    )
    client = NetworkClient(
        settings=settings,
        transport_factory=lambda _: DummyTransport(settings),
    )
    client._ensure_dispatch_control()

    calls = {"count": 0}

    async def slow_handler(envelope: WsEnvelope) -> None:
        calls["count"] += 1
        await asyncio.sleep(0.05)

    client.register_handler("biz.test", slow_handler)
    envelope = _make_envelope(settings, "biz.test", "env-1")

    await client._dispatch(envelope)
    assert calls["count"] == 1

    await client._dispatch(envelope)
    assert calls["count"] == 1
