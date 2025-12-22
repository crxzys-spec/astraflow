"""Frame-related helpers for the run registry."""

from __future__ import annotations

import copy
import logging
from typing import Any, Dict, List, Optional, Tuple

from scheduler_api.models.start_run_request_workflow import StartRunRequestWorkflow
from scheduler_api.models.workflow_subgraph import WorkflowSubgraph

from .graph import build_edge_bindings_for_workflow
from .middleware import extract_middleware_entries
from .models import (
    FrameDefinition,
    FrameRuntimeState,
    NodeState,
    RunRecord,
    WorkflowScopeIndex,
    _utc_now,
)

LOGGER = logging.getLogger(__name__)
CONTAINER_PARAMS_KEY = "__container"


def get_node_subgraph_id(node: Any) -> Optional[str]:
    params = getattr(node, "parameters", None)
    if isinstance(params, dict):
        container_params = params.get(CONTAINER_PARAMS_KEY)
        if isinstance(container_params, dict):
            value = container_params.get("subgraphId")
            if isinstance(value, str):
                value = value.strip()
                if value:
                    return value
    return None


def build_container_frames(
    workflow: StartRunRequestWorkflow,
) -> Tuple[Dict[str, FrameDefinition], Dict[Tuple[Optional[str], str], FrameDefinition]]:
    frames: Dict[str, FrameDefinition] = {}
    frames_by_parent: Dict[Tuple[Optional[str], str], FrameDefinition] = {}
    subgraph_lookup: Dict[str, WorkflowSubgraph] = {
        str(subgraph.id): subgraph for subgraph in (workflow.subgraphs or []) if getattr(subgraph, "id", None)
    }

    def clone_workflow(subgraph: WorkflowSubgraph) -> Optional[StartRunRequestWorkflow]:
        def _normalise_ids(definition: Dict[str, Any]) -> Dict[str, Any]:
            """Ensure workflow/subgraph ids and related fields are plain strings (not UUIDs)."""
            if "id" in definition and not isinstance(definition["id"], str):
                definition["id"] = str(definition["id"])
            nodes = definition.get("nodes")
            if isinstance(nodes, list):
                cleaned_nodes = []
                for node_entry in nodes:
                    if not isinstance(node_entry, dict):
                        continue
                    entry = dict(node_entry)
                    if "id" in entry and not isinstance(entry["id"], str):
                        entry["id"] = str(entry["id"])
                    mws = entry.get("middlewares")
                    if isinstance(mws, list):
                        _mw_ids, mw_defs = extract_middleware_entries(mws)
                        entry["middlewares"] = mw_defs
                    entry = _normalise_ids(entry)  # recurse in case nested defs
                    cleaned_nodes.append(entry)
                definition["nodes"] = cleaned_nodes
            edges = definition.get("edges")
            if isinstance(edges, list):
                cleaned_edges = []
                for edge_entry in edges:
                    if not isinstance(edge_entry, dict):
                        continue
                    entry = dict(edge_entry)
                    src = entry.get("source")
                    if isinstance(src, dict) and "node" in src and not isinstance(src["node"], str):
                        src = dict(src)
                        src["node"] = str(src["node"])
                        entry["source"] = src
                    tgt = entry.get("target")
                    if isinstance(tgt, dict) and "node" in tgt and not isinstance(tgt["node"], str):
                        tgt = dict(tgt)
                        tgt["node"] = str(tgt["node"])
                        entry["target"] = tgt
                    if "id" in entry and not isinstance(entry["id"], str):
                        entry["id"] = str(entry["id"])
                    cleaned_edges.append(entry)
                definition["edges"] = cleaned_edges
            subgraphs = definition.get("subgraphs")
            if isinstance(subgraphs, list):
                cleaned_subgraphs = []
                for sub_entry in subgraphs:
                    if not isinstance(sub_entry, dict):
                        continue
                    entry = dict(sub_entry)
                    if "id" in entry and not isinstance(entry["id"], str):
                        entry["id"] = str(entry["id"])
                    sub_def = entry.get("definition")
                    if isinstance(sub_def, dict):
                        entry["definition"] = _normalise_ids(dict(sub_def))
                    cleaned_subgraphs.append(entry)
                definition["subgraphs"] = cleaned_subgraphs
            return definition

        definition = subgraph.definition or {}
        if hasattr(definition, "to_dict"):
            definition = definition.to_dict()  # type: ignore[assignment]
        elif hasattr(definition, "model_dump"):
            definition = definition.model_dump(by_alias=True, exclude_none=True)  # type: ignore[assignment]
        definition_dict = copy.deepcopy(definition)
        if not isinstance(definition_dict, dict):
            LOGGER.warning("Unexpected subgraph definition type for %s: %s", subgraph.id, type(definition_dict))
            return None
        if "id" not in definition_dict:
            definition_dict["id"] = str(subgraph.id)
        if "schemaVersion" not in definition_dict and workflow.schema_version:
            definition_dict["schemaVersion"] = workflow.schema_version
        # normalise metadata UUID-like fields to strings to satisfy request models
        metadata = definition_dict.get("metadata")
        if isinstance(metadata, dict):
            for key in ("originId", "ownerId", "createdBy", "updatedBy"):
                if key in metadata and not isinstance(metadata[key], str):
                    metadata[key] = str(metadata[key])
            definition_dict["metadata"] = metadata
        definition_dict = _normalise_ids(definition_dict)
        try:
            return StartRunRequestWorkflow.from_dict(definition_dict)
        except Exception as exc:  # noqa: BLE001
            LOGGER.warning("Failed to clone subgraph %s: %s", subgraph.id, exc)
            return None

    def walk(container_node_id: str, subgraph_id: str, alias_chain: Tuple[str, ...], parent_frame_id: Optional[str]) -> None:
        subgraph = subgraph_lookup.get(subgraph_id)
        if not subgraph:
            LOGGER.warning("Subgraph %s referenced by %s not found", subgraph_id, container_node_id)
            return
        frame_workflow = clone_workflow(subgraph)
        if frame_workflow is None:
            return
        frame_alias_chain = alias_chain + (container_node_id, subgraph_id)
        frame_id = "::".join(frame_alias_chain)
        frame_definition = FrameDefinition(
            frame_id=frame_id,
            container_node_id=container_node_id,
            subgraph_id=subgraph_id,
            workflow=frame_workflow,
            parent_frame_id=parent_frame_id,
            alias_chain=frame_alias_chain,
        )
        frames[frame_id] = frame_definition
        frames_by_parent[(parent_frame_id, container_node_id)] = frame_definition
        for child in frame_workflow.nodes or []:
            child_subgraph_id = get_node_subgraph_id(child)
            if child.type == "workflow.container" and child_subgraph_id:
                walk(str(child.id), str(child_subgraph_id), frame_alias_chain, frame_id)

    for node in workflow.nodes or []:
        subgraph_id = get_node_subgraph_id(node)
        if node.type == "workflow.container" and subgraph_id:
            walk(str(node.id), str(subgraph_id), (str(workflow.id) or "root",), None)

    return frames, frames_by_parent


def initialise_frame_runtime(record: RunRecord, frame: FrameDefinition) -> FrameRuntimeState:
    workflow = frame.workflow
    nodes: Dict[str, NodeState] = {}
    task_index: Dict[str, NodeState] = {}

    def _add_dependency(source_state: NodeState, target_state: NodeState) -> None:
        if target_state.node_id not in source_state.dependencies:
            source_state.dependencies.append(target_state.node_id)
            source_state.pending_dependencies += 1
        if source_state.node_id not in target_state.dependents:
            target_state.dependents.append(source_state.node_id)

    def _propagate_host_dependencies_to_first_middleware() -> None:
        """Ensure the first middleware in a chain inherits the host's upstream deps."""
        for node in workflow.nodes or []:
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

    for node in workflow.nodes or []:
        node_id = str(node.id)
        package = getattr(node, "package", None)
        package_name = package.name if package else ""
        package_version = package.version if package else ""
        parameters = copy.deepcopy(getattr(node, "parameters", {}) or {})
        role = getattr(node, "role", None)
        middleware_ids, middleware_defs = extract_middleware_entries(getattr(node, "middlewares", []) or [])
        task_namespace = frame.frame_id
        node_state = NodeState(
            node_id=node_id,
            task_id=f"{task_namespace}::{node_id}",
            node_type=node.type,
            package_name=package_name,
            package_version=package_version,
            parameters=parameters,
            concurrency_key=f"{record.run_id}:{task_namespace}:{node_id}",
            frame_id=frame.frame_id,
            container_node_id=frame.container_node_id,
            subgraph_id=frame.subgraph_id,
            frame_alias=frame.alias_chain,
            middlewares=middleware_ids,
            middleware_defs=middleware_defs,
            chain_blocked=bool(middleware_ids),
        )
        if role:
            node_state.metadata = node_state.metadata or {}
            node_state.metadata["role"] = role
        nodes[node_id] = node_state
        task_index[node_state.task_id] = node_state

        for index, mw_def in enumerate(middleware_defs):
            mw_id = middleware_ids[index] if index < len(middleware_ids) else mw_def.get("id")
            if not mw_id or mw_id in nodes:
                continue
            mw_package = mw_def.get("package") if isinstance(mw_def, dict) else {}
            mw_state = NodeState(
                node_id=str(mw_id),
                task_id=f"{task_namespace}::{mw_id}",
                node_type=str(mw_def.get("type", "")) if isinstance(mw_def, dict) else "",
                package_name=str(mw_package.get("name", "")) if isinstance(mw_package, dict) else "",
                package_version=str(mw_package.get("version", "")) if isinstance(mw_package, dict) else "",
                parameters=copy.deepcopy(mw_def.get("parameters", {}) if isinstance(mw_def, dict) else {}),
                concurrency_key=f"{record.run_id}:{task_namespace}:{mw_id}",
                middlewares=[],
                middleware_defs=[],
                frame_id=frame.frame_id,
                container_node_id=frame.container_node_id,
                subgraph_id=frame.subgraph_id,
                frame_alias=frame.alias_chain,
                metadata={"role": "middleware", "host_node_id": node_id, "chain_index": index},
                chain_blocked=index > 0,
            )
            nodes[mw_state.node_id] = mw_state
            task_index[mw_state.task_id] = mw_state

    for edge in workflow.edges or []:
        source = getattr(edge.source, "node", None)
        target = getattr(edge.target, "node", None)
        source = str(source) if source is not None else None
        target = str(target) if target is not None else None
        if not source or not target:
            continue
        if source not in nodes or target not in nodes:
            continue
        target_state = nodes[target]
        source_state = nodes[source]
        target_state.dependencies.append(source)
        target_state.pending_dependencies += 1
        source_state.dependents.append(target)

    # First middleware waits for the same upstream dependencies as its host
    _propagate_host_dependencies_to_first_middleware()
    _wire_middleware_chain_dependencies()

    scope_index = WorkflowScopeIndex(workflow)
    edge_bindings = build_edge_bindings_for_workflow(workflow, scope_index, extract_middleware_entries)
    frame_state = FrameRuntimeState(
        definition=frame,
        nodes=nodes,
        task_index=task_index,
        scope_index=scope_index,
        edge_bindings=edge_bindings,
        status="running",
        started_at=_utc_now(),
    )
    return frame_state


def activate_frame(record: RunRecord, frame: FrameDefinition) -> FrameRuntimeState:
    frame_state = initialise_frame_runtime(record, frame)
    record.active_frames[frame.frame_id] = frame_state
    record.frame_stack.append(frame.frame_id)
    return frame_state


def pop_frame(record: RunRecord, frame_id: str) -> None:
    record.active_frames.pop(frame_id, None)
    if record.frame_stack and record.frame_stack[-1] == frame_id:
        record.frame_stack.pop()
        return
    if frame_id in record.frame_stack:
        record.frame_stack = [fid for fid in record.frame_stack if fid != frame_id]


def current_frame(record: RunRecord) -> Optional[FrameRuntimeState]:
    if not record.frame_stack:
        return None
    return record.active_frames.get(record.frame_stack[-1])
