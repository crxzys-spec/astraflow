import asyncio
from datetime import datetime, timezone

import pytest

from scheduler_api.control_plane.run_registry import RunRegistry
from scheduler_api.models.start_run_request import StartRunRequest
from scheduler_api.models.start_run_request_workflow import StartRunRequestWorkflow
def _basic_workflow() -> StartRunRequestWorkflow:
    return StartRunRequestWorkflow.from_dict(
        {
            "id": "wf-cancel",
            "schemaVersion": "2025-10",
            "metadata": {"name": "cancel-retry", "namespace": "default"},
            "nodes": [
                {
                    "id": "node-1",
                    "type": "example.pkg.source",
                    "package": {"name": "example.pkg", "version": "1.0.0"},
                    "status": "published",
                    "category": "test",
                    "label": "Source",
                    "position": {"x": 0, "y": 0},
                }
            ],
            "edges": [],
        }
    )


@pytest.mark.asyncio
async def test_worker_cancel_resets_node_for_retry():
    registry = RunRegistry()
    workflow = _basic_workflow()
    request = StartRunRequest(workflow=workflow, client_id="client-1")
    await registry.create_run(run_id="run-cancel", request=request, tenant="t")

    # simulate dispatch so node is in running state
    await registry.mark_dispatched(
        "run-cancel",
        worker_name="worker-1",
        task_id="task-1",
        node_id="node-1",
        node_type="example.pkg.source",
        package_name="example.pkg",
        package_version="1.0.0",
        seq_used=1,
        resource_refs=None,
        affinity=None,
        dispatch_id="dispatch-1",
        ack_deadline=datetime.now(timezone.utc),
    )

    record = await registry.reset_after_worker_cancel("run-cancel", node_id="node-1", task_id="task-1")
    assert record is not None
    node = record.nodes["node-1"]
    assert node.status == "queued"
    assert node.worker_name is None
    ready = await registry.collect_ready_nodes("run-cancel")
    assert ready, "Node should be ready for retry after worker cancel"
    assert ready[0].node_id == "node-1"
