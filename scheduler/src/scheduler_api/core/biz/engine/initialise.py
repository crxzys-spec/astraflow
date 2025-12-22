"""Run bootstrap helpers for the scheduler control plane."""

from __future__ import annotations

import copy
import hashlib
import json
from typing import Dict

from scheduler_api.models.start_run_request import StartRunRequest
from scheduler_api.models.start_run_request_workflow import StartRunRequestWorkflow

from ..domain.frames import build_container_frames
from ..domain.graph import build_edge_bindings
from ..domain.middleware import extract_middleware_entries
from ..domain.models import NodeState, RunRecord, WorkflowScopeIndex


def compute_definition_hash(workflow: StartRunRequestWorkflow) -> str:
    payload = workflow.to_dict()
    # Ensure any uuid.UUID (or other non-JSON types) are rendered deterministically.
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def initialise_nodes(record: RunRecord) -> None:
    nodes: Dict[str, NodeState] = {}

    def _propagate_host_dependencies_to_first_middleware() -> None:
        """Ensure the first middleware in a chain inherits the host's upstream dependencies."""
        for node in record.workflow.nodes or []:
            mw_ids, _ = extract_middleware_entries(getattr(node, "middlewares", []) or [])
            if not mw_ids:
                continue
            host_state = nodes.get(str(node.id))
            first_mw_state = nodes.get(str(mw_ids[0]))
            if not host_state or not first_mw_state:
                continue
            for dep_id in list(host_state.dependencies):
                if dep_id == first_mw_state.node_id:
                    continue
                if dep_id not in first_mw_state.dependencies:
                    first_mw_state.dependencies.append(dep_id)
                    first_mw_state.pending_dependencies += 1
                dep_state = nodes.get(dep_id)
                if dep_state and first_mw_state.node_id not in dep_state.dependents:
                    dep_state.dependents.append(first_mw_state.node_id)

    def _wire_middleware_chain_dependencies() -> None:
        """Order middleware chain execution and gate the host until the chain completes."""
        # Execution order is driven by middleware.next; dependencies are not used to sequence the chain.
        return

    for node in record.workflow.nodes or []:
        node_id = str(node.id)
        package = getattr(node, "package", None)
        package_name = package.name if package else ""
        package_version = package.version if package else ""
        parameters = copy.deepcopy(getattr(node, "parameters", {}) or {})
        role = getattr(node, "role", None)
        middleware_ids, middleware_defs = extract_middleware_entries(getattr(node, "middlewares", []) or [])
        node_state = NodeState(
            node_id=node_id,
            task_id=node_id,
            node_type=node.type,
            package_name=package_name,
            package_version=package_version,
            parameters=parameters,
            concurrency_key=f"{record.run_id}:{node_id}",
            middlewares=middleware_ids,
            middleware_defs=middleware_defs,
            chain_blocked=bool(middleware_ids),
        )
        if role:
            node_state.metadata = node_state.metadata or {}
            node_state.metadata["role"] = role
        nodes[node_id] = node_state
        record.task_index[node_state.task_id] = node_state

        for index, mw_def in enumerate(middleware_defs):
            mw_id = middleware_ids[index] if index < len(middleware_ids) else mw_def.get("id")
            if not mw_id or mw_id in nodes:
                continue
            mw_package = mw_def.get("package") if isinstance(mw_def, dict) else {}
            mw_state = NodeState(
                node_id=str(mw_id),
                task_id=str(mw_id),
                node_type=str(mw_def.get("type", "")) if isinstance(mw_def, dict) else "",
                package_name=str(mw_package.get("name", "")) if isinstance(mw_package, dict) else "",
                package_version=str(mw_package.get("version", "")) if isinstance(mw_package, dict) else "",
                parameters=copy.deepcopy(mw_def.get("parameters", {}) if isinstance(mw_def, dict) else {}),
                concurrency_key=f"{record.run_id}:{mw_id}",
                middlewares=[],
                middleware_defs=[],
                metadata={"role": "middleware", "host_node_id": node_id, "chain_index": index},
                chain_blocked=index > 0,
            )
            nodes[mw_state.node_id] = mw_state
            record.task_index[mw_state.task_id] = mw_state

    for edge in record.workflow.edges or []:
        source = getattr(edge.source, "node", None)
        target = getattr(edge.target, "node", None)
        source = str(source) if source is not None else None
        target = str(target) if target is not None else None
        if not source or not target:
            continue
        if target not in nodes or source not in nodes:
            continue
        target_state = nodes[target]
        source_state = nodes[source]
        target_state.dependencies.append(source)
        target_state.pending_dependencies += 1
        source_state.dependents.append(target)

    # First middleware waits for the same upstream dependencies as its host.
    _propagate_host_dependencies_to_first_middleware()
    _wire_middleware_chain_dependencies()

    record.nodes = nodes
    record.scope_index = WorkflowScopeIndex(record.workflow)
    record.edge_bindings = build_edge_bindings(record, extract_middleware_entries)


def build_run_record(*, run_id: str, request: StartRunRequest, tenant: str) -> RunRecord:
    workflow = request.workflow
    definition_hash = compute_definition_hash(workflow)
    record = RunRecord(
        run_id=run_id,
        definition_hash=definition_hash,
        client_id=request.client_id,
        workflow=workflow,
        tenant=tenant,
    )
    initialise_nodes(record)
    frames, frames_by_parent = build_container_frames(workflow)
    record.frames = frames
    record.frames_by_parent = frames_by_parent
    return record
