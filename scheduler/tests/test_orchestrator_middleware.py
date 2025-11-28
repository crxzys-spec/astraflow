import pytest

from scheduler_api.control_plane.orchestrator import RunOrchestrator
from scheduler_api.control_plane.run_registry import DispatchRequest


def _request(**overrides) -> DispatchRequest:
    base = dict(
        run_id="run-1",
        tenant="tenant",
        node_id="node-host",
        task_id="task-1",
        node_type="type",
        package_name="pkg",
        package_version="1.0.0",
        parameters={},
        resource_refs=[],
        affinity=None,
        concurrency_key="ck",
        seq=1,
    )
    base.update(overrides)
    return DispatchRequest(**base)


@pytest.mark.parametrize(
    "kwargs",
    [
        # host dispatch without middleware chain
        {},
        # middleware dispatch with matching chain/index
        {
            "node_id": "mw-1",
            "host_node_id": "node-host",
            "middleware_chain": ["mw-1", "mw-2"],
            "chain_index": 0,
        },
    ],
)
def test_validate_middleware_metadata_happy(kwargs):
    RunOrchestrator._validate_middleware_metadata(_request(**kwargs))


@pytest.mark.parametrize(
    "kwargs",
    [
        # middleware missing host id
        {"node_id": "mw-1", "middleware_chain": ["mw-1"], "chain_index": 0},
        # chain_index out of bounds
        {
            "node_id": "mw-1",
            "host_node_id": "node-host",
            "middleware_chain": ["mw-1"],
            "chain_index": 2,
        },
        # chain_index does not match chain entry
        {
            "node_id": "mw-2",
            "host_node_id": "node-host",
            "middleware_chain": ["mw-1", "mw-2"],
            "chain_index": 0,
        },
        # host dispatch must not include chain_index
        {
            "node_id": "node-host",
            "host_node_id": "node-host",
            "middleware_chain": ["mw-1"],
            "chain_index": 0,
        },
    ],
)
def test_validate_middleware_metadata_raises(kwargs):
    with pytest.raises(ValueError):
        RunOrchestrator._validate_middleware_metadata(_request(**kwargs))
