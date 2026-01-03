import asyncio

import pytest

from scheduler_api.engine.events import emit
from scheduler_api.domain.models import NodeState, RunRecord
from scheduler_api.models.start_run_request_workflow import StartRunRequestWorkflow


def _make_workflow() -> StartRunRequestWorkflow:
    return StartRunRequestWorkflow.from_dict(
        {
            "id": "wf-1",
            "schemaVersion": "2025-10",
            "metadata": {"name": "emit-tests"},
            "nodes": [
                {
                    "id": "node-1",
                    "type": "example.pkg.task",
                    "package": {"name": "example.pkg", "version": "1.0.0"},
                    "status": "published",
                    "category": "test",
                    "label": "Test",
                    "position": {"x": 0, "y": 0},
                }
            ],
            "edges": [],
        }
    )


def _make_record(status: str = "queued") -> RunRecord:
    return RunRecord(
        run_id="run-1",
        definition_hash="hash",
        client_id="client",
        workflow=_make_workflow(),
        tenant="tenant",
        status=status,
    )


@pytest.mark.asyncio
async def test_enqueue_node_state_and_snapshot():
    record = _make_record()
    node = NodeState(node_id="node-1", task_id="task-1")
    calls = []

    async def publish_node_state(rec, state):
        calls.append(("state", rec.run_id, state.node_id))

    async def publish_node_snapshot(rec, state, *, complete):
        calls.append(("snapshot", rec.run_id, state.node_id, complete))

    tasks = []
    emit.enqueue_node_state_and_snapshot(
        tasks,
        publish_node_state,
        publish_node_snapshot,
        record,
        node,
        complete=True,
    )
    await asyncio.gather(*tasks)

    expected = [
        ("state", "run-1", "node-1"),
        ("snapshot", "run-1", "node-1", True),
    ]
    assert sorted(calls) == sorted(expected)


@pytest.mark.asyncio
async def test_enqueue_run_state_if_changed():
    record = _make_record(status="running")

    async def publish_run_state(_record):
        return None

    tasks = []
    emit.enqueue_run_state_if_changed(
        tasks,
        publish_run_state,
        record,
        previous_status="running",
    )
    assert tasks == []

    emit.enqueue_run_state_if_changed(
        tasks,
        publish_run_state,
        record,
        previous_status="queued",
    )
    assert len(tasks) == 1
    await asyncio.gather(*tasks)


@pytest.mark.asyncio
async def test_enqueue_state_events():
    record = _make_record()
    node_a = NodeState(node_id="node-a", task_id="task-a")
    node_b = NodeState(node_id="node-b", task_id="task-b")
    calls = []

    async def publish_node_state(rec, state):
        calls.append(("node", rec.run_id, state.node_id))

    async def publish_run_snapshot(rec):
        calls.append(("run", rec.run_id))

    tasks = []
    emit.enqueue_state_events(
        tasks,
        publish_node_state,
        publish_run_snapshot,
        [(record, node_a), (record, node_b)],
    )
    await asyncio.gather(*tasks)

    assert sorted(calls) == sorted(
        [
            ("node", "run-1", "node-a"),
            ("run", "run-1"),
            ("node", "run-1", "node-b"),
            ("run", "run-1"),
        ]
    )


@pytest.mark.asyncio
async def test_enqueue_chunk_result_deltas_builds_payload():
    record = _make_record()
    node = NodeState(node_id="node-1", task_id="task-1")
    calls = []

    async def publish_node_result_delta(
        rec,
        state,
        *,
        revision,
        sequence,
        operation,
        path,
        payload,
        chunk_meta,
        terminal,
    ):
        calls.append(
            {
                "revision": revision,
                "sequence": sequence,
                "operation": operation,
                "path": path,
                "payload": payload,
                "chunk_meta": chunk_meta,
                "terminal": terminal,
            }
        )

    chunk_events = [
        {
            "revision": 2,
            "sequence": 3,
            "chunk": {
                "channel": "stdout",
                "text": "hello",
                "metadata": {"terminal": True},
            },
        }
    ]
    tasks = []
    emit.enqueue_chunk_result_deltas(
        tasks,
        publish_node_result_delta,
        record,
        node,
        chunk_events,
    )
    await asyncio.gather(*tasks)

    assert calls == [
        {
            "revision": 2,
            "sequence": 3,
            "operation": "append",
            "path": "/channels/stdout",
            "payload": {"text": "hello"},
            "chunk_meta": {"channel": "stdout", "metadata": {"terminal": True}},
            "terminal": True,
        }
    ]


@pytest.mark.asyncio
async def test_enqueue_result_deltas_builds_payload():
    record = _make_record()
    node = NodeState(node_id="node-1", task_id="task-1")
    calls = []

    async def publish_node_result_delta(
        rec,
        state,
        *,
        revision,
        sequence,
        operation,
        path,
        payload,
        chunk_meta,
        terminal,
    ):
        calls.append(
            {
                "revision": revision,
                "sequence": sequence,
                "operation": operation,
                "path": path,
                "payload": payload,
                "chunk_meta": chunk_meta,
                "terminal": terminal,
            }
        )

    result_deltas = [
        {
            "revision": 1,
            "sequence": 1,
            "operation": "replace",
            "path": "/results/value",
            "value": 7,
        },
        {
            "revision": 1,
            "sequence": 2,
            "operation": "remove",
            "path": "/results/old",
        },
    ]
    tasks = []
    emit.enqueue_result_deltas(
        tasks,
        publish_node_result_delta,
        record,
        node,
        result_deltas,
    )
    await asyncio.gather(*tasks)

    assert calls == [
        {
            "revision": 1,
            "sequence": 1,
            "operation": "replace",
            "path": "/results/value",
            "payload": {"value": 7},
            "chunk_meta": None,
            "terminal": False,
        },
        {
            "revision": 1,
            "sequence": 2,
            "operation": "remove",
            "path": "/results/old",
            "payload": None,
            "chunk_meta": None,
            "terminal": False,
        },
    ]
