import pytest

from scheduler_api.control_plane.run_registry import EdgeBinding, RunRegistry, WorkflowScopeIndex
from scheduler_api.models.start_run_request import StartRunRequest
from shared.models.ws import result as ws_result
from scheduler_api.models.start_run_request_workflow import StartRunRequestWorkflow


def _build_workflow_with_middleware_handle(middleware_id: str) -> StartRunRequestWorkflow:
    return StartRunRequestWorkflow.from_dict(
        {
            "id": "wf-1",
            "schemaVersion": "2025-10",
            "metadata": {
                "name": "middleware-edge-binding",
                "namespace": "default",
                "originId": "wf-1",
            },
            "nodes": [
                {
                    "id": "source-node",
                    "type": "example.pkg.source",
                    "package": {"name": "example.pkg", "version": "1.0.0"},
                    "status": "published",
                    "category": "test",
                    "label": "Source",
                    "position": {"x": 0, "y": 0},
                    "ui": {
                        "outputPorts": [
                            {"key": "out", "label": "Out", "binding": {"path": "/results/value", "mode": "read"}},
                        ]
                    },
                },
                {
                    "id": "host-node",
                    "type": "example.pkg.host",
                    "package": {"name": "example.pkg", "version": "1.0.0"},
                    "status": "published",
                    "category": "test",
                    "label": "Host",
                    "position": {"x": 1, "y": 0},
                    "middlewares": [
                        {
                            "id": middleware_id,
                            "type": "system.loop_middleware",
                            "package": {"name": "system", "version": "1.0.0"},
                            "status": "published",
                            "category": "system",
                            "label": "Loop",
                            "parameters": {"times": 1},
                            "ui": {
                                "inputPorts": [
                                    {
                                        "key": "times",
                                        "label": "Times",
                                        "binding": {"path": "/parameters/times", "mode": "write"},
                                    }
                                ]
                            },
                        }
                    ],
                },
            ],
            "edges": [
                {
                    "id": "edge-1",
                    "source": {"node": "source-node", "port": "out"},
                    "target": {"node": "host-node", "port": f"mw:{middleware_id}:input:times"},
                }
            ],
        }
    )


def test_middleware_edge_binding_handles_dict_entries():
    middleware_id = "mw-1"
    workflow = _build_workflow_with_middleware_handle(middleware_id)
    registry = RunRegistry()

    bindings = registry._build_edge_bindings_for_workflow(workflow, WorkflowScopeIndex(workflow))

    assert "source-node" in bindings
    edge_bindings = bindings["source-node"]
    assert len(edge_bindings) == 1

    binding = edge_bindings[0]
    assert isinstance(binding, EdgeBinding)
    assert binding.source_root == "results"
    assert binding.source_path == ["value"]
    assert binding.target_node == middleware_id
    assert binding.target_root == "parameters"
    assert binding.target_path == ["times"]


@pytest.mark.asyncio
async def test_edge_binding_applies_to_middleware_parameters():
    middleware_id = "mw-apply"
    workflow = _build_workflow_with_middleware_handle(middleware_id)
    registry = RunRegistry()
    request = StartRunRequest(
        workflow=workflow,
        client_id="client",
    )
    await registry.create_run(run_id="run-1", request=request, tenant="t")
    # simulate source node completion with result payload
    payload = ws_result.ResultPayload(
        run_id="run-1",
        task_id="source-node",
        status=ws_result.Status.SUCCEEDED,
        result={"value": 42},
        metadata=None,
        artifacts=None,
        duration_ms=None,
        error=None,
    )
    await registry.record_result("run-1", payload)
    run_snapshot = await registry.get("run-1")
    middleware_state = run_snapshot.nodes.get(middleware_id)
    assert middleware_state is not None
    assert middleware_state.parameters.get("times") == 42
