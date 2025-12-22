import pytest

from scheduler_api.control_plane.biz.domain.graph import build_edge_bindings_for_workflow
from scheduler_api.control_plane.biz.domain.middleware import extract_middleware_entries
from scheduler_api.control_plane.biz.domain.models import EdgeBinding, WorkflowScopeIndex
from scheduler_api.control_plane.run_state_service import RunStateService
from scheduler_api.models.start_run_request import StartRunRequest
from scheduler_api.models.start_run_request_workflow import StartRunRequestWorkflow
from shared.models.biz.exec.next.request import ExecMiddlewareNextRequest
from shared.models.biz.exec.result import ExecResultPayload, Status as ExecStatus

SUBGRAPH_ID = "sub-1"
SUBGRAPH_WORKFLOW_ID = "00000000-0000-0000-0000-000000000001"
SUBGRAPH_INNER_NODE_ID = "00000000-0000-0000-0000-000000000002"


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
    bindings = build_edge_bindings_for_workflow(
        workflow,
        WorkflowScopeIndex(workflow),
        extract_middleware_entries,
    )

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
    registry = RunStateService()
    request = StartRunRequest(
        workflow=workflow,
        client_id="client",
    )
    await registry.create_run(run_id="run-1", request=request, tenant="t")
    # simulate source node completion with result payload
    payload = ExecResultPayload(
        run_id="run-1",
        task_id="source-node",
        status=ExecStatus.SUCCEEDED,
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
            "metadata": {
                "name": "wf-next",
                "namespace": "default",
                "originId": "wf-next",
            },
            "nodes": [
                {
                    "id": "host",
                    "type": "example.pkg.host",
                    "package": {"name": "example.pkg", "version": "1.0.0"},
                    "status": "published",
                    "category": "test",
                    "label": "Host",
                    "position": {"x": 0, "y": 0},
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
            "metadata": {
                "name": "wf-container",
                "namespace": "default",
                "originId": "wf-container",
            },
            "nodes": [
                {
                    "id": "container",
                    "type": "workflow.container",
                    "package": {"name": "system", "version": "1.0.0"},
                    "status": "published",
                    "category": "system",
                    "label": "Container",
                    "position": {"x": 0, "y": 0},
                    "parameters": {"__container": {"subgraphId": SUBGRAPH_ID}},
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
                    "id": SUBGRAPH_ID,
                    "alias": SUBGRAPH_ID,
                    "definition": {
                        "id": SUBGRAPH_WORKFLOW_ID,
                        "schemaVersion": "2025-10",
                        "metadata": {
                            "name": "subgraph",
                            "namespace": "default",
                        },
                        "nodes": [
                            {
                                "id": SUBGRAPH_INNER_NODE_ID,
                                "type": "example.pkg.inner",
                                "package": {"name": "example.pkg", "version": "1.0.0"},
                                "status": "published",
                                "category": "test",
                                "label": "Inner",
                                "position": {"x": 0, "y": 0},
                            }
                        ],
                        "edges": [],
                    },
                }
            ],
        }
    )


def _build_single_middleware_workflow() -> StartRunRequestWorkflow:
    return StartRunRequestWorkflow.from_dict(
        {
            "id": "wf-rollup",
            "schemaVersion": "2025-10",
            "metadata": {
                "name": "middleware-rollup",
                "namespace": "default",
                "originId": "wf-rollup",
            },
            "nodes": [
                {
                    "id": "host-single",
                    "type": "example.pkg.host",
                    "package": {"name": "example.pkg", "version": "1.0.0"},
                    "status": "published",
                    "category": "test",
                    "label": "Host",
                    "position": {"x": 0, "y": 0},
                    "middlewares": [
                        {
                            "id": "mw-single",
                            "type": "system.loop_middleware",
                            "package": {"name": "system", "version": "1.0.0"},
                            "status": "published",
                            "category": "system",
                            "label": "Loop",
                        }
                    ],
                }
            ],
            "edges": [],
        }
    )


@pytest.mark.asyncio
async def test_middleware_chain_requires_next_to_progress():
    workflow = _build_two_middleware_workflow()
    registry = RunStateService()
    request = StartRunRequest(workflow=workflow, client_id="client")
    await registry.create_run(run_id="run-next", request=request, tenant="t")

    ready = await registry.collect_ready_nodes("run-next")
    assert [req.node_id for req in ready] == ["mw-1"]

    payload = ExecResultPayload(
        run_id="run-next",
        task_id="mw-1",
        status=ExecStatus.SUCCEEDED,
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

    next_req = ExecMiddlewareNextRequest(
        requestId="req-1",
        runId="run-next",
        nodeId="host",
        middlewareId="mw-1",
        chainIndex=0,
    )
    advance_ready, error = await registry.handle_next_request(
        next_req,
        worker_name="worker-1",
        worker_instance_id="worker-1",
    )
    assert error is None
    assert [req.node_id for req in advance_ready] == ["mw-2"]


@pytest.mark.asyncio
async def test_container_next_response_emitted_on_frame_completion():
    workflow = _build_container_with_middleware_workflow()
    registry = RunStateService()
    request = StartRunRequest(workflow=workflow, client_id="client")
    await registry.create_run(run_id="run-container", request=request, tenant="t")

    ready = await registry.collect_ready_nodes("run-container")
    assert [req.node_id for req in ready] == ["mw-c"]

    next_req = ExecMiddlewareNextRequest(
        requestId="req-container",
        runId="run-container",
        nodeId="container",
        middlewareId="mw-c",
        chainIndex=0,
    )
    frame_ready, error = await registry.handle_next_request(
        next_req,
        worker_name="worker-1",
        worker_instance_id="worker-1",
    )
    assert error is None
    assert len(frame_ready) == 1
    inner_dispatch = frame_ready[0]
    assert inner_dispatch.node_id == SUBGRAPH_INNER_NODE_ID

    inner_payload = ExecResultPayload(
        run_id="run-container",
        task_id=inner_dispatch.task_id,
        status=ExecStatus.SUCCEEDED,
        result={"done": True},
        metadata=None,
        artifacts=None,
        duration_ms=None,
        error=None,
    )
    _, _, next_responses = await registry.record_result("run-container", inner_payload)
    assert len(next_responses) == 1
    worker_name, response = next_responses[0]
    assert worker_name == "worker-1"
    assert response.requestId == "req-container"
    assert response.middlewareId == "mw-c"


@pytest.mark.asyncio
async def test_middleware_completion_finalises_rollup():
    workflow = _build_single_middleware_workflow()
    registry = RunStateService()
    request = StartRunRequest(workflow=workflow, client_id="client")
    await registry.create_run(run_id="run-finish", request=request, tenant="t")

    ready = await registry.collect_ready_nodes("run-finish")
    assert [req.node_id for req in ready] == ["mw-single"]

    next_req = ExecMiddlewareNextRequest(
        requestId="req-finish",
        runId="run-finish",
        nodeId="host-single",
        middlewareId="mw-single",
        chainIndex=0,
    )
    host_ready, error = await registry.handle_next_request(
        next_req,
        worker_name="worker-1",
        worker_instance_id="worker-1",
    )
    assert error is None
    assert [req.node_id for req in host_ready] == ["host-single"]
    host_dispatch = host_ready[0]

    host_payload = ExecResultPayload(
        run_id="run-finish",
        task_id=host_dispatch.task_id,
        status=ExecStatus.SUCCEEDED,
        result={"ok": True},
        metadata=None,
        artifacts=None,
        duration_ms=None,
        error=None,
    )
    await registry.record_result("run-finish", host_payload)

    mw_payload = ExecResultPayload(
        run_id="run-finish",
        task_id="mw-single",
        status=ExecStatus.SUCCEEDED,
        result={"done": True},
        metadata=None,
        artifacts=None,
        duration_ms=None,
        error=None,
    )
    await registry.record_result("run-finish", mw_payload)

    snapshot = await registry.get("run-finish")
    assert snapshot is not None
    assert snapshot.status == "succeeded"
    assert snapshot.nodes["mw-single"].status == "succeeded"
    assert snapshot.nodes["host-single"].status == "succeeded"


@pytest.mark.asyncio
async def test_next_rejected_while_container_frame_active():
    workflow = _build_container_with_middleware_workflow()
    registry = RunStateService()
    request = StartRunRequest(workflow=workflow, client_id="client")
    await registry.create_run(run_id="run-busy", request=request, tenant="t")

    ready = await registry.collect_ready_nodes("run-busy")
    mw_dispatch = ready[0]
    await registry.mark_dispatched(
        "run-busy",
        worker_name="worker-1",
        task_id=mw_dispatch.task_id,
        node_id=mw_dispatch.node_id,
        node_type=mw_dispatch.node_type,
        package_name=mw_dispatch.package_name,
        package_version=mw_dispatch.package_version,
        seq_used=mw_dispatch.seq,
    )

    next_req = ExecMiddlewareNextRequest(
        requestId="req-start",
        runId="run-busy",
        nodeId="container",
        middlewareId="mw-c",
        chainIndex=0,
    )
    frame_ready, error = await registry.handle_next_request(
        next_req,
        worker_name="worker-1",
        worker_instance_id="worker-1",
    )
    assert error is None
    assert frame_ready
    inner_dispatch = frame_ready[0]
    await registry.mark_dispatched(
        inner_dispatch.run_id,
        worker_name="worker-1",
        task_id=inner_dispatch.task_id,
        node_id=inner_dispatch.node_id,
        node_type=inner_dispatch.node_type,
        package_name=inner_dispatch.package_name,
        package_version=inner_dispatch.package_version,
        seq_used=inner_dispatch.seq,
    )

    next_req_again = ExecMiddlewareNextRequest(
        requestId="req-again",
        runId="run-busy",
        nodeId="container",
        middlewareId="mw-c",
        chainIndex=0,
    )
    frame_ready_again, error_again = await registry.handle_next_request(
        next_req_again,
        worker_name="worker-1",
        worker_instance_id="worker-1",
    )
    assert error_again == "next_target_not_ready"
    assert frame_ready_again == []


@pytest.mark.asyncio
async def test_next_request_recovers_stale_running_target():
    workflow = _build_single_middleware_workflow()
    registry = RunStateService()
    request = StartRunRequest(workflow=workflow, client_id="client")
    await registry.create_run(run_id="run-stale", request=request, tenant="t")

    ready = await registry.collect_ready_nodes("run-stale")
    mw_dispatch = ready[0]
    await registry.mark_dispatched(
        "run-stale",
        worker_name="worker-1",
        task_id=mw_dispatch.task_id,
        node_id=mw_dispatch.node_id,
        node_type=mw_dispatch.node_type,
        package_name=mw_dispatch.package_name,
        package_version=mw_dispatch.package_version,
        seq_used=mw_dispatch.seq,
    )

    # Simulate a stale host state where it is marked running without an active worker.
    async with registry._lock:  # noqa: SLF001
        host_state = registry._runs["run-stale"].nodes["host-single"]  # noqa: SLF001
        host_state.status = "running"
        host_state.worker_name = None
        host_state.pending_ack = False
        host_state.enqueued = False
        host_state.pending_dependencies = 0

    next_req = ExecMiddlewareNextRequest(
        requestId="req-stale",
        runId="run-stale",
        nodeId="host-single",
        middlewareId="mw-single",
        chainIndex=0,
    )
    host_ready, error = await registry.handle_next_request(
        next_req,
        worker_name="worker-1",
        worker_instance_id="worker-1",
    )
    assert error is None
    assert [req.node_id for req in host_ready] == ["host-single"]


@pytest.mark.asyncio
async def test_next_request_fails_when_target_not_ready():
    workflow = _build_single_middleware_workflow()
    registry = RunStateService()
    request = StartRunRequest(workflow=workflow, client_id="client")
    await registry.create_run(run_id="run-fail", request=request, tenant="t")

    ready = await registry.collect_ready_nodes("run-fail")
    mw_dispatch = ready[0]
    await registry.mark_dispatched(
        "run-fail",
        worker_name="worker-1",
        task_id=mw_dispatch.task_id,
        node_id=mw_dispatch.node_id,
        node_type=mw_dispatch.node_type,
        package_name=mw_dispatch.package_name,
        package_version=mw_dispatch.package_version,
        seq_used=mw_dispatch.seq,
    )

    # Simulate target host still marked running and enqueued so it is not ready.
    async with registry._lock:  # noqa: SLF001
        host_state = registry._runs["run-fail"].nodes["host-single"]  # noqa: SLF001
        host_state.status = "running"
        host_state.enqueued = True
        host_state.pending_dependencies = 1
        host_state.chain_blocked = True

    next_req = ExecMiddlewareNextRequest(
        requestId="req-fail",
        runId="run-fail",
        nodeId="host-single",
        middlewareId="mw-single",
        chainIndex=0,
    )
    host_ready, error = await registry.handle_next_request(
        next_req,
        worker_name="worker-1",
        worker_instance_id="worker-1",
    )
    assert host_ready == []
    assert error == "next_target_not_ready"

    snapshot = await registry.get("run-fail")
    assert snapshot is not None
    assert snapshot.status == "running"
    assert snapshot.nodes["host-single"].status == "running"

