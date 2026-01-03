"""Graph and binding propagation helpers for the run registry."""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Tuple

from scheduler_api.models.start_run_request_workflow import StartRunRequestWorkflow

from .bindings import (
    _MISSING,
    _get_nested_value,
    _parse_binding_path,
    _resolve_binding_reference,
    _set_nested_value,
)
from .models import (
    EdgeBinding,
    FrameRuntimeState,
    NodeState,
    RunRecord,
    WorkflowScopeIndex,
)

ExtractMiddlewareEntries = Callable[[Optional[Any]], Tuple[List[str], List[Dict[str, Any]]]]


def build_edge_bindings(
    record: RunRecord,
    extract_middleware_entries: ExtractMiddlewareEntries,
) -> Dict[str, List[EdgeBinding]]:
    return build_edge_bindings_for_workflow(record.workflow, record.scope_index, extract_middleware_entries)


def build_edge_bindings_for_workflow(
    workflow: StartRunRequestWorkflow,
    scope_index: Optional[WorkflowScopeIndex],
    extract_middleware_entries: ExtractMiddlewareEntries,
) -> Dict[str, List[EdgeBinding]]:
    workflow_nodes = {node.id: node for node in workflow.nodes or []}
    middleware_defs: Dict[str, Any] = {}
    for node in workflow.nodes or []:
        mw_ids, mw_entries = extract_middleware_entries(getattr(node, "middlewares", []) or [])
        for idx, mw_id in enumerate(mw_ids):
            middleware_defs[mw_id] = mw_entries[idx] if idx < len(mw_entries) else None
    bindings: Dict[str, List[EdgeBinding]] = {}

    def _resolve_port_binding(
        node_id: str, port_key: Optional[str], direction: str
    ) -> Tuple[Optional[Any], Optional[str]]:
        if not port_key:
            return None, None
        node_def = workflow_nodes.get(node_id)
        if not node_def:
            return None, None

        # middleware port handle: mw:{middlewareId}:{direction}:{portKey}
        if port_key.startswith("mw:"):
            try:
                _, mw_id, handle_dir, mw_port_key = port_key.split(":", 3)
            except ValueError:
                return None, None
            if handle_dir != ("output" if direction == "output" else "input"):
                return None, None
            middlewares = getattr(node_def, "middlewares", None) or []
            for mw in middlewares:
                mw_identifier = None
                if isinstance(mw, dict):
                    mw_identifier = mw.get("id") or mw.get("node_id") or mw.get("nodeId")
                else:
                    mw_identifier = getattr(mw, "id", None)
                if str(mw_identifier) != mw_id:
                    continue
                ui = mw.get("ui") if isinstance(mw, dict) else getattr(mw, "ui", None)
                if not ui:
                    continue
                ports = (
                    (ui.get("outputPorts") or ui.get("output_ports")) if isinstance(ui, dict) else ui.output_ports
                ) if handle_dir == "output" else (
                    (ui.get("inputPorts") or ui.get("input_ports")) if isinstance(ui, dict) else ui.input_ports
                )
                if not ports:
                    continue
                for port in ports:
                    port_key_value = port.get("key") if isinstance(port, dict) else getattr(port, "key", None)
                    if port_key_value != mw_port_key:
                        continue
                    binding = port.get("binding") if isinstance(port, dict) else getattr(port, "binding", None)
                    return binding, mw_id
            return None, None

        if not node_def.ui:
            return None, None
        ports = node_def.ui.output_ports if direction == "output" else node_def.ui.input_ports
        if not ports:
            return None, None
        for port in ports:
            if port.key == port_key:
                return getattr(port, "binding", None), node_id
        return None, None

    for edge in workflow.edges or []:
        source_node = getattr(edge.source, "node", None)
        target_node = getattr(edge.target, "node", None)
        if not source_node or not target_node:
            continue

        source_binding_model, source_binding_node = _resolve_port_binding(
            source_node, getattr(edge.source, "port", None), "output"
        )
        target_binding_model, target_binding_node = _resolve_port_binding(
            target_node, getattr(edge.target, "port", None), "input"
        )
        if not source_binding_model or not target_binding_model:
            continue

        def _binding_node_exists(node_id: Optional[str]) -> bool:
            if node_id is None:
                return False
            return node_id in workflow_nodes or node_id in middleware_defs

        if not _binding_node_exists(source_binding_node) or not _binding_node_exists(target_binding_node):
            continue

        source_binding = _resolve_binding_reference(
            source_binding_model,
            source_binding_node,
            scope_index if source_binding_node in workflow_nodes else None,
        )
        target_binding = _resolve_binding_reference(
            target_binding_model,
            target_binding_node,
            scope_index if target_binding_node in workflow_nodes else None,
        )
        if not source_binding or not target_binding:
            continue

        source_root, source_path = source_binding.root, source_binding.path
        target_root, target_path = target_binding.root, target_binding.path
        if target_root != "parameters":
            # Only parameter bindings are supported for edge propagation.
            continue

        entry = EdgeBinding(
            source_root=source_root,
            source_path=source_path,
            target_node=target_binding.node_id,
            target_root=target_root,
            target_path=target_path,
        )
        bindings.setdefault(source_binding.node_id, []).append(entry)

    return bindings


def apply_edge_bindings(record: RunRecord, node: NodeState) -> None:
    if not record.edge_bindings:
        return
    apply_edge_bindings_for_graph(node, record.edge_bindings, record.nodes)


def apply_middleware_output_bindings(host_state: NodeState, middleware_state: NodeState) -> None:
    """Project middleware output bindings onto the host node so downstream edges see emitted values."""

    middleware_defs = getattr(host_state, "middleware_defs", None) or []
    target_def: Optional[Dict[str, Any]] = None
    for candidate in middleware_defs:
        try:
            candidate_id = str(
                candidate.get("id") if isinstance(candidate, dict) else getattr(candidate, "id", None)
            )
        except Exception:
            candidate_id = None
        if candidate_id and candidate_id == middleware_state.node_id:
            target_def = candidate if isinstance(candidate, dict) else None
            break
    if not target_def:
        return

    ui = target_def.get("ui") if isinstance(target_def, dict) else None
    if not ui or not isinstance(ui, dict):
        return
    ports = ui.get("outputPorts") or ui.get("output_ports") or []
    if not ports:
        return

    for port in ports:
        if not isinstance(port, dict):
            continue
        binding = port.get("binding")
        raw_path = None
        if isinstance(binding, dict):
            raw_path = binding.get("path")
        elif isinstance(binding, str):
            raw_path = binding
        if not raw_path or not isinstance(raw_path, str):
            continue
        parsed = _parse_binding_path(raw_path)
        if not parsed:
            continue
        root, path = parsed
        source_container = middleware_state.parameters if root == "parameters" else middleware_state.result
        if not isinstance(source_container, dict):
            continue
        value = _get_nested_value(source_container, path)
        if value is _MISSING:
            continue

        if root == "parameters":
            if not isinstance(host_state.parameters, dict):
                host_state.parameters = {}
            target_container = host_state.parameters
        else:
            if not isinstance(host_state.result, dict):
                host_state.result = {}
            target_container = host_state.result
        _set_nested_value(target_container, path, value)


def apply_frame_edge_bindings(frame: FrameRuntimeState, node: NodeState) -> None:
    if not frame.edge_bindings:
        return
    apply_edge_bindings_for_graph(
        node,
        frame.edge_bindings,
        frame.nodes,
    )


def apply_edge_bindings_for_graph(
    node: NodeState,
    bindings: Dict[str, List[EdgeBinding]],
    graph_nodes: Dict[str, NodeState],
) -> None:
    if not node.result and not node.parameters:
        return
    entries = bindings.get(node.node_id)
    if not entries:
        return
    for entry in entries:
        if entry.source_root == "parameters":
            source_container = node.parameters
        else:
            source_container = node.result
        if not isinstance(source_container, dict):
            continue
        value = _get_nested_value(source_container, entry.source_path)
        if value is _MISSING:
            continue
        target_node = graph_nodes.get(entry.target_node)
        if not target_node:
            continue
        if entry.target_root == "parameters":
            target_container = target_node.parameters
            if not isinstance(target_container, dict):
                target_container = {}
                target_node.parameters = target_container
        else:
            target_container = target_node.result
            if not isinstance(target_container, dict):
                target_container = {}
                target_node.result = target_container
        _set_nested_value(target_container, entry.target_path, value)
