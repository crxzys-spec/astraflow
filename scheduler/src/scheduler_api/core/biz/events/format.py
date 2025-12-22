"""Formatting helpers for run registry snapshots and node state."""

from __future__ import annotations

import copy
import math
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, Optional

from scheduler_api.models.start_run_request_workflow import StartRunRequestWorkflow

if TYPE_CHECKING:
    from ..domain.models import NodeState, RunRecord


def extract_node_message(node: NodeState) -> Optional[str]:
    metadata = node.metadata or {}
    message = metadata.get("message") or metadata.get("statusMessage")
    if isinstance(message, str) and message.strip():
        return message
    return None


def extract_node_progress(node: NodeState) -> Optional[float]:
    metadata = node.metadata or {}
    raw = metadata.get("progress")
    try:
        value = float(raw)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    if not math.isfinite(value):
        return None
    return max(0.0, min(1.0, value))


def extract_node_stage(node: NodeState) -> str:
    metadata = node.metadata or {}
    stage_hint = metadata.get("stage")
    if isinstance(stage_hint, str):
        stage_hint = stage_hint.strip()
        if stage_hint:
            return stage_hint
    return node.status


def format_artifact(
    data: Dict[str, Any],
    *,
    default_worker_name: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "resourceId": data.get("resourceId") or data.get("resource_id"),
        "workerName": data.get("workerName") or data.get("worker_name") or default_worker_name,
        "type": data.get("type"),
        "sizeBytes": data.get("sizeBytes") or data.get("size_bytes"),
        "inline": data.get("inline"),
        "expiresAt": data.get("expiresAt") or data.get("expires_at"),
        "metadata": data.get("metadata"),
    }


def format_resource_ref(data: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "resourceId": data.get("resourceId") or data.get("resource_id"),
        "workerName": data.get("workerName") or data.get("worker_name"),
        "type": data.get("type"),
        "scope": data.get("scope"),
        "expiresAt": data.get("expiresAt") or data.get("expires_at"),
        "metadata": data.get("metadata"),
    }


def build_frame_metadata(
    node: NodeState,
    *,
    record: Optional[RunRecord] = None,
) -> Optional[Dict[str, Any]]:
    if not node.frame_id:
        return None
    frame_meta: Dict[str, Any] = {"frameId": node.frame_id}
    if node.container_node_id:
        frame_meta["containerNodeId"] = node.container_node_id
    if node.subgraph_id:
        frame_meta["subgraphId"] = node.subgraph_id
    if node.frame_alias:
        frame_meta["aliasChain"] = list(node.frame_alias)
    if record:
        frame_definition = record.frames.get(node.frame_id)
        if frame_definition:
            subgraph_name = getattr(
                getattr(frame_definition.workflow, "metadata", None),
                "name",
            )
            if subgraph_name:
                frame_meta["subgraphName"] = subgraph_name
    return frame_meta


def build_node_state_payload(
    node: NodeState,
    *,
    last_updated_at: Optional[datetime],
) -> Dict[str, Any]:
    state: Dict[str, Any] = {"stage": extract_node_stage(node)}
    progress = extract_node_progress(node)
    if progress is not None:
        state["progress"] = progress
    message = extract_node_message(node)
    if message:
        state["message"] = message
    if last_updated_at:
        state["lastUpdatedAt"] = last_updated_at.isoformat()
    elif node.metadata and isinstance(node.metadata.get("lastUpdatedAt"), str):
        state["lastUpdatedAt"] = node.metadata["lastUpdatedAt"]
    if node.error:
        state["error"] = node.error.to_dict()
    return state


def build_workflow_snapshot(record: RunRecord) -> StartRunRequestWorkflow:
    workflow_dict = record.workflow.to_dict()
    nodes = workflow_dict.get("nodes", [])
    for node_payload in nodes:
        node_id = node_payload.get("id")
        if not node_id:
            continue
        node_state = record.nodes.get(node_id)
        if not node_state:
            continue
        state_payload = build_node_state_payload(
            node_state,
            last_updated_at=node_state.finished_at or node_state.started_at,
        )
        node_payload["state"] = state_payload
    return StartRunRequestWorkflow.from_dict(workflow_dict)


def format_node(
    node: NodeState,
    *,
    record: Optional[RunRecord] = None,
) -> Dict[str, Any]:
    node_id = str(node.node_id) if node.node_id is not None else None
    task_id = str(node.task_id) if node.task_id is not None else None
    payload: Dict[str, Any] = {
        "nodeId": node_id,
        "taskId": task_id,
        "status": node.status,
    }
    if node.worker_name:
        payload["workerName"] = node.worker_name
    if node.started_at:
        payload["startedAt"] = node.started_at
    if node.finished_at:
        payload["finishedAt"] = node.finished_at
    if node.seq is not None:
        payload["seq"] = node.seq
    if node.pending_ack:
        payload["pendingAck"] = True
    if node.dispatch_id:
        payload["dispatchId"] = node.dispatch_id
    if node.ack_deadline:
        payload["ackDeadline"] = node.ack_deadline
    if node.resource_refs:
        payload["resourceRefs"] = [
            format_resource_ref(ref) for ref in node.resource_refs
        ]
    if node.affinity:
        payload["affinity"] = node.affinity
    if node.artifacts:
        payload["artifacts"] = [
            format_artifact(
                artifact,
                default_worker_name=record.worker_name if record else None,
            )
            for artifact in node.artifacts
        ]
    if node.result is not None:
        payload["result"] = node.result
    metadata_source = copy.deepcopy(node.metadata) if node.metadata else {}
    frame_metadata = build_frame_metadata(node, record=record)
    if frame_metadata:
        metadata_source["__frame"] = frame_metadata
    if metadata_source:
        # expose middleware chain/host markers for trace UIs
        if getattr(node, "middlewares", None):
            middleware_defs = getattr(node, "middleware_defs", []) or []
            metadata_source["middlewares"] = middleware_defs if middleware_defs else list(node.middlewares)
        if node.metadata and "host_node_id" in node.metadata:
            metadata_source["host_node_id"] = node.metadata.get("host_node_id")
        if node.metadata and "chain_index" in node.metadata:
            metadata_source["chain_index"] = node.metadata.get("chain_index")
        payload["metadata"] = metadata_source
    if node.error:
        payload["error"] = node.error.to_dict()
    state_payload = build_node_state_payload(
        node,
        last_updated_at=node.finished_at or node.started_at,
    )
    if state_payload:
        payload["state"] = state_payload
    return payload
