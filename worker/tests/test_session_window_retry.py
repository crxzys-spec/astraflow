import asyncio

import pytest

from worker.config import WorkerSettings
from worker.network.session import Session
from worker.network.transport.dummy import DummyTransport


class _FakeConn:
    def __init__(self) -> None:
        self.sent = []

    async def send(self, message: dict) -> None:
        self.sent.append(message)

    async def stop(self) -> None:
        return None


async def _wait_for(predicate, *, timeout: float = 0.2, interval: float = 0.01) -> bool:
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while loop.time() < deadline:
        if predicate():
            return True
        await asyncio.sleep(interval)
    return predicate()


@pytest.mark.asyncio
async def test_window_retry_drop_releases_send_credit():
    settings = WorkerSettings(
        session_window_size=1,
        ack_retry_base_ms=1,
        ack_retry_max_ms=2,
        ack_retry_attempts=1,
    )
    session = Session(settings=settings, transport_factory=lambda _: DummyTransport(settings))
    session._ensure_windows()
    session._conn = _FakeConn()

    message = {"type": "biz.test", "id": "msg-1"}
    seq = await session._assign_session_seq(message)
    assert seq == 1

    session._register_window(message, seq)

    try:
        cleared = await _wait_for(lambda: seq not in session._pending_window)
        assert cleared, "pending window should clear after retries are exhausted"
        assert seq not in session._seq_to_message_id
        await asyncio.wait_for(session._send_credit.acquire(), timeout=0.05)
        session._send_credit.release()
    finally:
        await session.stop()
