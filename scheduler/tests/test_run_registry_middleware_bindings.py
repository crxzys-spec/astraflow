import pytest

from scheduler_api.control_plane.run_registry import EdgeBinding, RunRegistry, WorkflowScopeIndex
from scheduler_api.models.start_run_request import StartRunRequest
from scheduler_api.models.start_run_request_workflow import StartRunRequestWorkflow
from shared.models.ws import result as ws_result
from shared.models.ws.next import NextRequestPayload


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


def _build_two_middleware_workflow() -> StartRunRequestWorkflow:
    return StartRunRequestWorkflow.from_dict(
        {
            "id": "wf-next",
            "schemaVersion": "2025-10",
            "nodes": [
                {
                    "id": "host",
                    "type": "example.pkg.host",
                    "package": {"name": "example.pkg", "version": "1.0.0"},
                    "status": "published",
                    "category": "test",
                    "label": "Host",
                    "middlewares": [
                        {
                            "id": "mw-1",
                            "type": "system.loop_middleware",
                            "package": {"name": "system", "version": "1.0.0"},
                            "status": "published",
                            "category": "system",
                            "label": "First",
                        },
                        {
                            "id": "mw-2",
                            "type": "system.loop_middleware",
                            "package": {"name": "system", "version": "1.0.0"},
                            "status": "published",
                            "category": "system",
                            "label": "Second",
                        },
                    ],
                }
            ],
            "edges": [],
        }
    )


def _build_container_with_middleware_workflow() -> StartRunRequestWorkflow:
    return StartRunRequestWorkflow.from_dict(
        {
            "id": "wf-container",
            "schemaVersion": "2025-10",
            "nodes": [
                {
                    "id": "container",
                    "type": "workflow.container",
                    "package": {"name": "system", "version": "1.0.0"},
                    "status": "published",
                    "category": "system",
                    "label": "Container",
                    "parameters": {"__container": {"subgraphId": "sub-1"}},
                    "middlewares": [
                        {
                            "id": "mw-c",
                            "type": "system.loop_middleware",
                            "package": {"name": "system", "version": "1.0.0"},
                            "status": "published",
                            "category": "system",
                            "label": "ContainerMW",
                        }
                    ],
                }
            ],
            "edges": [],
            "subgraphs": [
                {
                    "id": "sub-1",
                    "alias": "sub-1",
                    "definition": {
                        "id": "sub-1",
                        "schemaVersion": "2025-10",
                        "nodes": [
                            {
                                "id": "inner",
                                "type": "example.pkg.inner",
                                "package": {"name": "example.pkg", "version": "1.0.0"},
                                "status": "published",
                                "category": "test",
                                "label": "Inner",
                            }
                        ],
                        "edges": [],
                    },
                }
            ],
        }
    )


@pytest.mark.asyncio
async def test_middleware_chain_requires_next_to_progress():
    workflow = _build_two_middleware_workflow()
    registry = RunRegistry()
    request = StartRunRequest(workflow=workflow, client_id="client")
    await registry.create_run(run_id="run-next", request=request, tenant="t")

    ready = await registry.collect_ready_nodes("run-next")
    assert [req.node_id for req in ready] == ["mw-1"]

    payload = ws_result.ResultPayload(
        run_id="run-next",
        task_id="mw-1",
        status=ws_result.Status.SUCCEEDED,
        result={},
        metadata=None,
        artifacts=None,
        duration_ms=None,
        error=None,
    )
    _, ready_after, next_responses = await registry.record_result("run-next", payload)
    assert ready_after == []
    assert next_responses == []
    assert await registry.collect_ready_nodes("run-next") == []

    next_req = NextRequestPayload(
        requestId="req-1",
        runId="run-next",
        nodeId="host",
        middlewareId="mw-1",
        chainIndex=0,
    )
    advance_ready, error = await registry.handle_next_request(next_req, worker_id="worker-1")
    assert error is None
    assert [req.node_id for req in advance_ready] == ["mw-2"]


@pytest.mark.asyncio
async def test_container_next_response_emitted_on_frame_completion():
    workflow = _build_container_with_middleware_workflow()
    registry = RunRegistry()
    request = StartRunRequest(workflow=workflow, client_id="client")
    await registry.create_run(run_id="run-container", request=request, tenant="t")

    ready = await registry.collect_ready_nodes("run-container")
    assert [req.node_id for req in ready] == ["mw-c"]

    mw_payload = ws_result.ResultPayload(
        run_id="run-container",
        task_id="mw-c",
        status=ws_result.Status.SUCCEEDED,
        result={},
        metadata=None,
        artifacts=None,
        duration_ms=None,
        error=None,
    )
    await registry.record_result("run-container", mw_payload)
    assert await registry.collect_ready_nodes("run-container") == []

    next_req = NextRequestPayload(
        requestId="req-container",
        runId="run-container",
        nodeId="container",
        middlewareId="mw-c",
        chainIndex=0,
    )
    frame_ready, error = await registry.handle_next_request(next_req, worker_id="worker-1")
    assert error is None
    assert len(frame_ready) == 1
    inner_dispatch = frame_ready[0]
    assert inner_dispatch.node_id.endswith("inner") or inner_dispatch.node_id == "inner"

    inner_payload = ws_result.ResultPayload(
        run_id="run-container",
        task_id=inner_dispatch.task_id,
        status=ws_result.Status.SUCCEEDED,
        result={"done": True},
        metadata=None,
        artifacts=None,
        duration_ms=None,
        error=None,
    )
    _, _, next_responses = await registry.record_result("run-container", inner_payload)
    assert len(next_responses) == 1
    worker_id, response = next_responses[0]
    assert worker_id == "worker-1"
    assert response.request_id == "req-container"
    assert response.middleware_id == "mw-c"
