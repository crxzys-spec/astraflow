"""In-memory run tracking for the scheduler control plane."""

from __future__ import annotations

import asyncio
import copy
import hashlib
import json
import logging
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple
from uuid import UUID

from scheduler_api.models.list_runs200_response import ListRuns200Response
from scheduler_api.models.list_runs200_response_items_inner import ListRuns200ResponseItemsInner
from scheduler_api.models.list_runs200_response_items_inner_artifacts_inner import (
    ListRuns200ResponseItemsInnerArtifactsInner,
)
from scheduler_api.models.list_runs200_response_items_inner_error import (
    ListRuns200ResponseItemsInnerError,
)
from scheduler_api.models.list_runs200_response_items_inner_nodes_inner import (
    ListRuns200ResponseItemsInnerNodesInner,
)
from scheduler_api.models.start_run202_response import StartRun202Response
from scheduler_api.models.start_run_request import StartRunRequest
from scheduler_api.models.start_run_request_workflow import StartRunRequestWorkflow
from scheduler_api.models.workflow_subgraph import WorkflowSubgraph
from scheduler_api.sse import event_publisher
from scheduler_api.sse.mappers import (
    node_result_delta_envelope,
    node_result_snapshot_envelope,
    node_state_envelope,
    run_snapshot_envelope,
    run_state_envelope,
)
from shared.models.ws import result as ws_result
from shared.models.ws.error import ErrorPayload
from shared.models.ws.feedback import FeedbackPayload
from shared.models.ws.next import NextRequestPayload, NextResponsePayload

LOGGER = logging.getLogger(__name__)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _compute_definition_hash(workflow: StartRunRequestWorkflow) -> str:
    payload = workflow.to_dict()
    # Ensure any uuid.UUID (or other non-JSON types) are rendered deterministically
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _normalise_status(value: str) -> str:
    mapping = {
        "succeeded": "succeeded",
        "failed": "failed",
        "skipped": "succeeded",
        "cancelled": "cancelled",
        "queued": "queued",
        "running": "running",
    }
    return mapping.get(value.lower(), value.lower())


def _encode_pointer_segment(segment: str) -> str:
    return str(segment).replace("~", "~0").replace("/", "~1")


def _merge_result_updates(
    target: Dict[str, Any],
    updates: Dict[str, Any],
    path_prefix: str = "",
) -> List[Dict[str, Any]]:
    deltas: List[Dict[str, Any]] = []
    for key, value in updates.items():
        pointer = f"{path_prefix}/{_encode_pointer_segment(key)}" if path_prefix else f"/{_encode_pointer_segment(key)}"
        if value is None:
            if key in target:
                target.pop(key, None)
                deltas.append({"path": pointer, "value": None, "operation": "remove"})
            continue
        if isinstance(value, dict):
            if value:
                existing = target.get(key)
                if isinstance(existing, dict):
                    deltas.extend(_merge_result_updates(existing, value, pointer))
                    continue
                new_value = copy.deepcopy(value)
                if existing != new_value:
                    target[key] = new_value
                    deltas.append({"path": pointer, "value": new_value, "operation": "replace"})
            else:
                if target.get(key) != {}:
                    target[key] = {}
                    deltas.append({"path": pointer, "value": {}, "operation": "replace"})
            continue
        new_value = copy.deepcopy(value) if isinstance(value, (dict, list)) else value
        if target.get(key) != new_value:
            target[key] = new_value
            deltas.append({"path": pointer, "value": new_value, "operation": "replace"})
    return deltas


FINAL_STATUSES = {"succeeded", "failed", "cancelled"}
CONTAINER_PARAMS_KEY = "__container"


def _get_node_subgraph_id(node: Any) -> Optional[str]:
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


_MISSING = object()


def _decode_pointer(segment: str) -> str:
    return segment.replace("~1", "/").replace("~0", "~")


def _parse_binding_path(path: Optional[str]) -> Optional[Tuple[str, List[str]]]:
    if not path:
        return None
    segments: List[str]
    if path.startswith("/"):
        segments = [_decode_pointer(part) for part in path.split("/") if part]
    else:
        raw_segments = path.replace("[", ".").replace("]", "").split(".")
        segments = [segment for segment in raw_segments if segment]
    if not segments:
        return None
    root = segments[0]
    if root not in {"parameters", "results"}:
        return None
    return root, segments[1:]


@dataclass(frozen=True)
class BindingScopeHint:
    kind: Optional[str]
    subgraph_aliases: Tuple[str, ...]
    node_id: Optional[str]
    raw_prefix: Optional[str] = None

    def alias_chain(self) -> Tuple[str, ...]:
        return self.subgraph_aliases


@dataclass
class BindingResolution:
    node_id: str
    root: str
    path: List[str]


class WorkflowScopeIndex:
    """Maintains alias/subgraph metadata for resolving scoped bindings within a workflow."""

    def __init__(self, workflow: StartRunRequestWorkflow):
        self.node_ids: Set[str] = {
            node.id for node in (workflow.nodes or []) if getattr(node, "id", None)
        }
        self.subgraphs = {}
        self.alias_paths: Dict[str, Tuple[str, ...]] = {}
        self.node_memberships: Dict[str, Set[Tuple[str, ...]]] = {}

        for raw in workflow.subgraphs or []:
            alias = getattr(raw, "alias", None) or getattr(raw, "id", None)
            if not alias:
                continue
            self.subgraphs[alias] = raw
        self._initialise_alias_paths()

    def _initialise_alias_paths(self) -> None:
        for alias in self.subgraphs:
            chain = self._build_chain(alias)
            if chain:
                self.alias_paths[alias] = chain
        for alias, subgraph in self.subgraphs.items():
            chain = self.alias_paths.get(alias)
            if not chain:
                continue
            node_ids = self._extract_node_ids(subgraph)
            for node_id in node_ids:
                if node_id not in self.node_ids:
                    continue
                self.node_memberships.setdefault(node_id, set()).add(chain)

    def _extract_node_ids(self, subgraph: Any) -> List[str]:
        definition = getattr(subgraph, "definition", None)
        if definition is None:
            definition = getattr(subgraph, "definition_", None)
        if definition is None:
            return []
        nodes = getattr(definition, "nodes", None)
        if nodes is None and isinstance(definition, dict):
            nodes = definition.get("nodes")
        if not nodes:
            return []
        extracted: List[str] = []
        for node in nodes:
            node_id = getattr(node, "id", None)
            if node_id is None and isinstance(node, dict):
                node_id = node.get("id")
            if node_id:
                extracted.append(node_id)
        return extracted

    def _build_chain(self, alias: str) -> Tuple[str, ...]:
        chain: List[str] = []
        current = alias
        visited: Set[str] = set()
        while current:
            if current in visited:
                break
            visited.add(current)
            chain.insert(0, current)
            subgraph = self.subgraphs.get(current)
            parent = getattr(subgraph, "parent_alias", None)
            if parent is None:
                metadata = getattr(subgraph, "metadata", None)
                if isinstance(metadata, dict):
                    parent = metadata.get("parentAlias")
            current = parent
        return tuple(chain)

    def resolve_node(self, hint: Optional[BindingScopeHint], fallback_node: Optional[str]) -> Optional[str]:
        node_id = fallback_node
        if hint and hint.node_id:
            node_id = hint.node_id
        if not node_id or node_id not in self.node_ids:
            return None
        if not hint:
            return node_id
        alias_chain = hint.alias_chain()
        if not alias_chain:
            return node_id
        if self._node_matches_alias_chain(node_id, alias_chain):
            return node_id
        return None

    def _node_matches_alias_chain(self, node_id: str, alias_chain: Tuple[str, ...]) -> bool:
        memberships = self.node_memberships.get(node_id)
        if not memberships:
            return False
        for membership in memberships:
            if len(alias_chain) > len(membership):
                continue
            if membership[-len(alias_chain):] == alias_chain:
                return True
        return False


def _parse_scope_prefix(prefix: str) -> Optional[BindingScopeHint]:
    text = prefix.strip()
    if not text:
        return None
    if text.startswith("@"):
        tokens = [token for token in text[1:].split(".") if token]
        node_id = None
        aliases: List[str] = []
        for token in tokens:
            if token.startswith("#"):
                node_id = token[1:] or None
            else:
                aliases.append(token)
        if not aliases:
            return None
        subgraph_aliases: Tuple[str, ...] = tuple(aliases)
        return BindingScopeHint(
            kind="subgraph",
            subgraph_aliases=subgraph_aliases,
            node_id=node_id,
            raw_prefix=text,
        )
    if text.startswith("#"):
        return BindingScopeHint(
            kind="local",
            subgraph_aliases=tuple(),
            node_id=text[1:] or None,
            raw_prefix=text,
        )
    return None


def _scope_hint_from_binding(binding: Any) -> Optional[BindingScopeHint]:
    scope_model = getattr(binding, "scope", None)
    prefix = getattr(binding, "prefix", None)
    if scope_model is not None:
        kind = getattr(scope_model, "kind", None)
        raw_prefix = getattr(scope_model, "prefix", None) or prefix
        subgraph_aliases = list(getattr(scope_model, "subgraph_aliases", []) or [])
        # Back-compat: legacy payloads may still include workflow_alias.
        workflow_alias = getattr(scope_model, "workflow_alias", None)
        if workflow_alias and workflow_alias not in subgraph_aliases:
            subgraph_aliases.insert(0, workflow_alias)
        node_id = getattr(scope_model, "node_id", None)
        return BindingScopeHint(
            kind=kind,
            subgraph_aliases=tuple(subgraph_aliases),
            node_id=node_id,
            raw_prefix=raw_prefix,
        )
    if prefix:
        return _parse_scope_prefix(prefix)
    return None


def _resolve_binding_reference(
    binding: Any,
    owning_node: Optional[str],
    scope_index: Optional[WorkflowScopeIndex],
) -> Optional[BindingResolution]:
    if binding is None:
        return None
    path_value = binding.get("path") if isinstance(binding, dict) else getattr(binding, "path", None)
    parsed = _parse_binding_path(path_value)
    if not parsed or owning_node is None:
        return None
    root, path = parsed
    target_node = owning_node
    if scope_index:
        hint = _scope_hint_from_binding(binding)
        resolved = scope_index.resolve_node(hint, owning_node)
        if not resolved:
            return None
        target_node = resolved
    return BindingResolution(node_id=target_node, root=root, path=path)


def _get_nested_value(container: Optional[Dict[str, Any]], path: List[str]) -> Any:
    current: Any = container
    for key in path:
        if not isinstance(current, dict):
            return _MISSING
        if key not in current:
            return _MISSING
        current = current[key]
    return copy.deepcopy(current)


def _ensure_container(container: Dict[str, Any], key: str) -> Dict[str, Any]:
    value = container.get(key)
    if isinstance(value, dict):
        return value
    new_value: Dict[str, Any] = {}
    container[key] = new_value
    return new_value


def _set_nested_value(container: Dict[str, Any], path: List[str], value: Any) -> None:
    if not path:
        if isinstance(value, dict):
            container.clear()
            container.update(copy.deepcopy(value))
        else:
            raise ValueError("Binding path must not be empty when assigning non-mapping values")
        return
    current = container
    for key in path[:-1]:
        current = _ensure_container(current, key)
    current[path[-1]] = copy.deepcopy(value)


@dataclass
class EdgeBinding:
    source_root: str
    source_path: List[str]
    target_node: str
    target_root: str
    target_path: List[str]


@dataclass
class DispatchRequest:
    run_id: str
    tenant: str
    node_id: str
    task_id: str
    node_type: str
    package_name: str
    package_version: str
    parameters: Dict[str, Any]
    resource_refs: List[Dict[str, Any]]
    affinity: Optional[Dict[str, Any]]
    concurrency_key: str
    seq: int
    preferred_worker_id: Optional[str] = None
    attempts: int = 0
    dispatch_id: Optional[str] = None
    host_node_id: Optional[str] = None
    middleware_chain: Optional[List[str]] = None
    chain_index: Optional[int] = None
    ack_deadline: Optional[datetime] = None


@dataclass
class NodeState:
    node_id: str
    task_id: str
    status: str = "queued"
    node_type: str = ""
    package_name: str = ""
    package_version: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    concurrency_key: str = ""
    worker_id: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    seq: Optional[int] = None
    resource_refs: List[Dict[str, Any]] = field(default_factory=list)
    affinity: Optional[Dict[str, Any]] = None
    artifacts: List[Dict[str, Any]] = field(default_factory=list)
    result: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    error: Optional[ListRuns200ResponseItemsInnerError] = None
    dependencies: List[str] = field(default_factory=list)
    dependents: List[str] = field(default_factory=list)
    pending_dependencies: int = 0
    enqueued: bool = False
    pending_ack: bool = False
    dispatch_id: Optional[str] = None
    ack_deadline: Optional[datetime] = None
    frame_id: Optional[str] = None
    container_node_id: Optional[str] = None
    subgraph_id: Optional[str] = None
    frame_alias: Tuple[str, ...] = field(default_factory=tuple)
    middlewares: List[str] = field(default_factory=list)
    middleware_defs: List[Dict[str, Any]] = field(default_factory=list)
    chain_blocked: bool = False


@dataclass
class FrameDefinition:
    frame_id: str
    container_node_id: str
    subgraph_id: str
    workflow: StartRunRequestWorkflow
    parent_frame_id: Optional[str]
    alias_chain: Tuple[str, ...]


@dataclass
class FrameRuntimeState:
    definition: FrameDefinition
    nodes: Dict[str, NodeState]
    task_index: Dict[str, NodeState]
    scope_index: WorkflowScopeIndex
    edge_bindings: Dict[str, List[EdgeBinding]]
    status: str = "idle"
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None

    @property
    def frame_id(self) -> str:
        return self.definition.frame_id

    @property
    def container_node_id(self) -> str:
        return self.definition.container_node_id

    @property
    def parent_frame_id(self) -> Optional[str]:
        return self.definition.parent_frame_id


@dataclass
class RunRecord:
    run_id: str
    definition_hash: str
    client_id: str
    workflow: StartRunRequestWorkflow
    tenant: str
    created_at: datetime = field(default_factory=_utc_now)
    status: str = "queued"
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    worker_id: Optional[str] = None
    task_id: Optional[str] = None
    node_id: Optional[str] = None
    node_type: Optional[str] = None
    package_name: Optional[str] = None
    package_version: Optional[str] = None
    next_seq: int = 1
    error: Optional[ListRuns200ResponseItemsInnerError] = None
    result_payload: Optional[Dict[str, Any]] = None
    duration_ms: Optional[int] = None
    artifacts: List[Dict[str, Any]] = field(default_factory=list)
    nodes: Dict[str, NodeState] = field(default_factory=dict)
    task_index: Dict[str, NodeState] = field(default_factory=dict)
    edge_bindings: Dict[str, List[EdgeBinding]] = field(default_factory=dict)
    scope_index: Optional[WorkflowScopeIndex] = None
    frames: Dict[str, "FrameDefinition"] = field(default_factory=dict)
    frames_by_parent: Dict[Tuple[Optional[str], str], "FrameDefinition"] = field(default_factory=dict)
    active_frames: Dict[str, "FrameRuntimeState"] = field(default_factory=dict)
    frame_stack: List[str] = field(default_factory=list)
    completed_frames: Dict[str, Dict[str, NodeState]] = field(default_factory=dict)


    def to_summary(self) -> ListRuns200ResponseItemsInner:
        artifacts = [
            ListRuns200ResponseItemsInnerArtifactsInner.from_dict(self._format_artifact(artifact))
            for artifact in self.artifacts
        ] if self.artifacts else None
        all_node_states: List[NodeState] = []
        if self.nodes:
            all_node_states.extend(self.nodes.values())
        if self.active_frames:
            for frame in self.active_frames.values():
                all_node_states.extend(frame.nodes.values())
        if self.completed_frames:
            for frame_nodes in self.completed_frames.values():
                all_node_states.extend(frame_nodes.values())
        nodes = [
            ListRuns200ResponseItemsInnerNodesInner.from_dict(self._format_node(node))
            for node in sorted(
                all_node_states,
                key=lambda n: (
                    0 if n.frame_id is None else 1,
                    len(n.frame_alias) if n.frame_alias else 0,
                    n.task_id or n.node_id,
                ),
            )
        ] if all_node_states else None
        return ListRuns200ResponseItemsInner(
            runId=self.run_id,
            status=self.status,
            definitionHash=self.definition_hash,
            clientId=self.client_id,
            startedAt=self.started_at,
            finishedAt=self.finished_at,
            error=self.error,
            artifacts=artifacts,
            nodes=nodes,
        )

    def to_start_response(self) -> StartRun202Response:
        return StartRun202Response(
            runId=self.run_id,
            status=self.status,
            definitionHash=self.definition_hash,
            clientId=self.client_id,
            createdAt=self.created_at,
        )

    def get_node(self, node_id: str, *, task_id: Optional[str] = None) -> NodeState:
        node = self.nodes.get(node_id)
        if not node:
            node = NodeState(node_id=node_id, task_id=task_id or node_id)
            self.nodes[node_id] = node
            if node.task_id:
                self.task_index[node.task_id] = node
        if task_id:
            previous_task = node.task_id
            node.task_id = task_id
            if previous_task and previous_task in self.task_index and self.task_index[previous_task] is node:
                self.task_index.pop(previous_task, None)
            self.task_index[task_id] = node
        return node

    def find_node_by_task(self, task_id: str) -> Optional[NodeState]:
        for node in self.nodes.values():
            if node.task_id == task_id:
                return node
        return None

    def refresh_rollup(self) -> None:
        if self.nodes:
            statuses = {node.status for node in self.nodes.values()}
            if "failed" in statuses:
                self.status = "failed"
            elif statuses.issubset({"queued"}):
                self.status = "queued"
            elif statuses.issubset({"succeeded"}):
                self.status = "succeeded"
            elif statuses.issubset(FINAL_STATUSES):
                if statuses == {"cancelled"}:
                    self.status = "cancelled"
                else:
                    self.status = "succeeded"
            else:
                self.status = "running"

            started_nodes = [node.started_at for node in self.nodes.values() if node.started_at]
            if started_nodes:
                self.started_at = min(started_nodes)
            finished = all(node.status in FINAL_STATUSES for node in self.nodes.values())
            if not finished and self.status == "failed":
                finished = True
            if finished:
                if not self.finished_at:
                    self.finished_at = _utc_now()
            else:
                self.finished_at = None

            self.artifacts = [
                artifact
                for node in self.nodes.values()
                for artifact in (node.artifacts or [])
            ]
            if self.status == "failed":
                failed_error = next((node.error for node in self.nodes.values() if node.error), None)
                self.error = failed_error
            elif self.status == "succeeded":
                self.error = None

    def _format_artifact(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "resourceId": data.get("resourceId") or data.get("resource_id"),
            "workerId": data.get("workerId") or data.get("worker_id") or self.worker_id,
            "type": data.get("type"),
            "sizeBytes": data.get("sizeBytes") or data.get("size_bytes"),
            "inline": data.get("inline"),
            "expiresAt": data.get("expiresAt") or data.get("expires_at"),
            "metadata": data.get("metadata"),
        }

    def _format_resource_ref(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "resourceId": data.get("resourceId") or data.get("resource_id"),
            "workerId": data.get("workerId") or data.get("worker_id"),
            "type": data.get("type"),
            "scope": data.get("scope"),
            "expiresAt": data.get("expiresAt") or data.get("expires_at"),
            "metadata": data.get("metadata"),
        }

    def _extract_node_message(self, node: NodeState) -> Optional[str]:
        if not node.metadata:
            return None
        message = node.metadata.get("message") or node.metadata.get("statusMessage")
        if isinstance(message, str) and message.strip():
            return message
        return None

    def _extract_node_progress(self, node: NodeState) -> Optional[float]:
        if not node.metadata:
            return None
        raw = node.metadata.get("progress")
        try:
            value = float(raw)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return None
        if not math.isfinite(value):
            return None
        return max(0.0, min(1.0, value))

    def _build_node_state_payload(
        self,
        node: NodeState,
        *,
        last_updated_at: Optional[datetime],
    ) -> Dict[str, Any]:
        metadata = node.metadata or {}
        stage_hint = metadata.get("stage")
        stage_value = (
            stage_hint.strip()
            if isinstance(stage_hint, str) and stage_hint.strip()
            else node.status
        )
        state: Dict[str, Any] = {"stage": stage_value}
        progress = self._extract_node_progress(node)
        if progress is not None:
            state["progress"] = progress
        message = self._extract_node_message(node)
        if message:
            state["message"] = message
        if last_updated_at:
            state["lastUpdatedAt"] = last_updated_at.isoformat()
        elif node.metadata and isinstance(node.metadata.get("lastUpdatedAt"), str):
            state["lastUpdatedAt"] = node.metadata["lastUpdatedAt"]
        if node.error:
            state["error"] = node.error.to_dict()
        return state

    def _build_workflow_snapshot(self, record: RunRecord) -> StartRunRequestWorkflow:
        workflow_dict = record.workflow.to_dict()
        nodes = workflow_dict.get("nodes", [])
        for node_payload in nodes:
            node_id = node_payload.get("id")
            if not node_id:
                continue
            node_state = record.nodes.get(node_id)
            if not node_state:
                continue
            state_payload = self._build_node_state_payload(
                node_state,
                last_updated_at=node_state.finished_at or node_state.started_at,
            )
            node_payload["state"] = state_payload
        return StartRunRequestWorkflow.from_dict(workflow_dict)

    def _build_frame_metadata(self, node: NodeState) -> Optional[Dict[str, Any]]:
        if not node.frame_id:
            return None
        frame_meta: Dict[str, Any] = {"frameId": node.frame_id}
        if node.container_node_id:
            frame_meta["containerNodeId"] = node.container_node_id
        if node.subgraph_id:
            frame_meta["subgraphId"] = node.subgraph_id
        if node.frame_alias:
            frame_meta["aliasChain"] = list(node.frame_alias)
        frame_definition = self.frames.get(node.frame_id)
        if frame_definition:
            subgraph_name = getattr(
                getattr(frame_definition.workflow, "metadata", None),
                "name",
                None,
            )
            if subgraph_name:
                frame_meta["subgraphName"] = subgraph_name
        return frame_meta

    def _format_node(self, node: NodeState) -> Dict[str, Any]:
        node_id = str(node.node_id) if node.node_id is not None else None
        task_id = str(node.task_id) if node.task_id is not None else None
        payload: Dict[str, Any] = {
            "nodeId": node_id,
            "taskId": task_id,
            "status": node.status,
        }
        if node.worker_id:
            payload["workerId"] = node.worker_id
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
                self._format_resource_ref(ref) for ref in node.resource_refs
            ]
        if node.affinity:
            payload["affinity"] = node.affinity
        if node.artifacts:
            payload["artifacts"] = [
                self._format_artifact(artifact) for artifact in node.artifacts
            ]
        if node.result is not None:
            payload["result"] = node.result
        metadata_source = copy.deepcopy(node.metadata) if node.metadata else {}
        frame_metadata = self._build_frame_metadata(node)
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
        state_payload = self._build_node_state_payload(
            node,
            last_updated_at=node.finished_at or node.started_at,
        )
        if state_payload:
            payload["state"] = state_payload
        return payload


NEXT_ERROR_MESSAGES: Dict[str, str] = {
    "next_run_finalised": "run already in final status",
    "next_duplicate": "duplicate next request",
    "next_no_chain": "middleware chain not found",
    "next_invalid_chain": "invalid chain index",
    "next_target_not_ready": "target node not ready",
    "next_timeout": "next request timed out",
    "next_cancelled": "next request cancelled",
    "next_unavailable": "next request rejected",
}


class RunRegistry:
    """Thread-safe run registry to coordinate REST and WebSocket layers."""

    def __init__(self) -> None:
        self._runs: Dict[str, RunRecord] = {}
        self._lock = asyncio.Lock()
        # pending middleware next requests keyed by request_id -> (run_id, worker_id, deadline, node_id, middleware_id, target_task_id)
        self._pending_next_requests: Dict[str, Tuple[str, Optional[str], Optional[datetime], Optional[str], Optional[str], Optional[str]]] = {}
        self._next_error_messages = NEXT_ERROR_MESSAGES

    @staticmethod
    def _is_middleware_node(node: NodeState) -> bool:
        return bool(node.metadata and node.metadata.get("role") == "middleware")

    def _is_host_with_middleware(self, node: NodeState) -> bool:
        return bool(node.middlewares) and not self._is_middleware_node(node)

    def _is_container_node(self, node: NodeState) -> bool:
        if node.node_type == "workflow.container":
            return True
        return bool(node.metadata and node.metadata.get("role") == "container")

    def _is_container_ready(self, node: NodeState) -> bool:
        if not self._is_container_node(node):
            return False
        if node.middlewares:
            # Containers with middleware still follow the middleware chain rules.
            return False
        if getattr(node, "chain_blocked", False):
            return False
        return node.status == "queued" and node.pending_dependencies == 0 and not node.enqueued

    def _is_first_middleware(self, node: NodeState) -> bool:
        if not self._is_middleware_node(node):
            return False
        chain_index = node.metadata.get("chain_index") if node.metadata else None
        return chain_index is None or chain_index == 0

    def _should_auto_dispatch(self, node: NodeState) -> bool:
        if node.status != "queued" or node.pending_dependencies != 0 or node.enqueued:
            return False
        if getattr(node, "chain_blocked", False):
            return False
        if self._is_host_with_middleware(node):
            return False
        return True

    def _release_dependents(
        self,
        record: RunRecord,
        node_state: NodeState,
        frame_state: Optional[FrameRuntimeState],
        ready: List[DispatchRequest],
    ) -> None:
        """Release dependents of a completed node into the ready queue."""
        graph_nodes = frame_state.nodes if frame_state else record.nodes
        for dependent_id in node_state.dependents:
            dependent = graph_nodes.get(dependent_id)
            if not dependent or dependent.status != "queued":
                continue
            if dependent.pending_dependencies > 0:
                dependent.pending_dependencies -= 1
            if getattr(dependent, "chain_blocked", False):
                continue
            if self._is_container_node(dependent):
                if dependent.pending_dependencies > 0 or dependent.enqueued:
                    continue
                parent_frame_id = frame_state.frame_id if frame_state else None
                frame_ready = self._start_container_execution(
                    record,
                    dependent,
                    parent_frame_id=parent_frame_id,
                )
                ready.extend(frame_ready)
                continue
            if self._is_host_with_middleware(dependent):
                if dependent.pending_dependencies == 0 and not dependent.enqueued:
                    ready.append(self._build_dispatch_request_for_node(record, dependent))
                continue
            if self._should_auto_dispatch(dependent):
                ready.append(self._build_dispatch_request_for_node(record, dependent))

    def _finalise_pending_next(
        self,
        payload: ws_result.ResultPayload,
        node_state: NodeState,
        *,
        status: str,
    ) -> List[Tuple[Optional[str], NextResponsePayload]]:
        """Send a terminal next_response for any middleware.next waiting on this task."""
        responses: List[Tuple[Optional[str], NextResponsePayload]] = []
        pending_next_to_clear = [
            (req_id, worker_id, run_id, node_id, middleware_id)
            for req_id, (run_id, worker_id, deadline, node_id, middleware_id, target_task_id)
            in self._pending_next_requests.items()
            if target_task_id == node_state.task_id
        ]
        for req_id, worker_id, run_id, node_id, middleware_id in pending_next_to_clear:
            self._pending_next_requests.pop(req_id, None)
            err_body = None
            if payload.error:
                err_body = {"code": payload.error.code, "message": payload.error.message}
            elif status != "succeeded":
                err_body = {"code": f"next_{status}", "message": f"target {node_state.node_id} status {status}"}
            resp = NextResponsePayload(
                requestId=req_id,
                runId=run_id,
                nodeId=node_id or "",
                middlewareId=middleware_id or "",
                result=node_state.result,
                error=err_body,
            )
            responses.append((worker_id, resp))
        return responses

    async def _publish_run_state(self, record: RunRecord) -> None:
        if not record.client_id:
            return
        envelope = run_state_envelope(
            tenant=record.tenant,
            client_session_id=record.client_id,
            run_id=record.run_id,
            status=record.status,
            started_at=record.started_at,
            finished_at=record.finished_at,
            reason=record.error.message if record.error else None,
            occurred_at=_utc_now(),
        )
        try:
            await event_publisher.publish(envelope)
        except Exception:  # noqa: BLE001
            LOGGER.exception("Failed to publish run state event run=%s", record.run_id)

    async def _publish_run_snapshot(self, record: RunRecord) -> None:
        if not record.client_id:
            return
        summary = record.to_summary()
        payload = summary.model_dump(by_alias=True, exclude_none=True, mode="json")
        nodes_payload = payload.pop("nodes", None)
        envelope = run_snapshot_envelope(
            tenant=record.tenant,
            client_session_id=record.client_id,
            run=payload,
            nodes=nodes_payload,
            occurred_at=_utc_now(),
        )
        try:
            await event_publisher.publish(envelope)
        except Exception:  # noqa: BLE001
            LOGGER.exception("Failed to publish run snapshot event run=%s", record.run_id)

    async def _publish_node_state(self, record: RunRecord, node: NodeState) -> None:
        if not record.client_id:
            return
        progress = self._extract_node_progress(node)
        message = self._extract_node_message(node)
        error_payload = node.error.to_dict() if node.error else None
        occurred_at = _utc_now()
        envelope = node_state_envelope(
            tenant=record.tenant,
            client_session_id=record.client_id,
            run_id=record.run_id,
            node_id=node.node_id,
            stage=node.status,
            progress=progress,
            message=message,
            error=error_payload,
            occurred_at=occurred_at,
            last_updated_at=occurred_at,
        )
        try:
            await event_publisher.publish(envelope)
        except Exception:  # noqa: BLE001
            LOGGER.exception(
                "Failed to publish node state event run=%s node=%s",
                record.run_id,
                node.node_id,
            )

    async def _publish_node_snapshot(
        self,
        record: RunRecord,
        node: NodeState,
        *,
        complete: bool,
    ) -> None:
        if not record.client_id:
            return
        content: Dict[str, Any]
        if isinstance(node.result, dict):
            content = node.result
        elif node.result is None:
            content = {}
        else:
            content = {"value": node.result}

        envelope = node_result_snapshot_envelope(
            tenant=record.tenant,
            client_session_id=record.client_id,
            run_id=record.run_id,
            node_id=node.node_id,
            revision=(node.seq or 0),
            content=content,
            artifacts=node.artifacts,
            complete=complete,
            summary=(
                node.error.message if node.error else node.metadata.get("message")
                if node.metadata
                else None
            ),
            occurred_at=_utc_now(),
        )
        try:
            await event_publisher.publish(envelope)
        except Exception:  # noqa: BLE001
            LOGGER.exception(
                "Failed to publish node result snapshot run=%s node=%s",
                record.run_id,
                node.node_id,
            )

    async def _publish_node_result_delta(
        self,
        record: RunRecord,
        node: NodeState,
        *,
        revision: int,
        sequence: int,
        operation: str,
        path: Optional[str],
        payload: Optional[Dict[str, Any]],
        chunk_meta: Optional[Dict[str, Any]],
        terminal: bool = False,
    ) -> None:
        if not record.client_id:
            return
        envelope = node_result_delta_envelope(
            tenant=record.tenant,
            client_session_id=record.client_id,
            run_id=record.run_id,
            node_id=node.node_id,
            revision=revision,
            sequence=sequence,
            operation=operation,
            path=path,
            payload=payload,
            chunk_meta=chunk_meta,
            terminal=terminal,
            occurred_at=_utc_now(),
        )
        try:
            await event_publisher.publish(envelope)
        except Exception:  # noqa: BLE001
            LOGGER.exception(
                "Failed to publish node result delta run=%s node=%s",
                record.run_id,
                node.node_id,
            )

    def _extract_node_message(self, node: NodeState) -> Optional[str]:
        metadata = node.metadata or {}
        message = metadata.get("message") or metadata.get("statusMessage")
        if isinstance(message, str) and message.strip():
            return message
        return None

    def _extract_node_progress(self, node: NodeState) -> Optional[float]:
        metadata = node.metadata or {}
        raw = metadata.get("progress")
        try:
            value = float(raw)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return None
        if not math.isfinite(value):
            return None
        return max(0.0, min(1.0, value))

    def _build_node_state_payload(
        self,
        node: NodeState,
        *,
        last_updated_at: Optional[datetime],
    ) -> Dict[str, Any]:
        state: Dict[str, Any] = {"stage": node.status}
        progress = self._extract_node_progress(node)
        if progress is not None:
            state["progress"] = progress
        message = self._extract_node_message(node)
        if message:
            state["message"] = message
        if last_updated_at:
            state["lastUpdatedAt"] = last_updated_at.isoformat()
        elif node.metadata and isinstance(node.metadata.get("lastUpdatedAt"), str):
            state["lastUpdatedAt"] = node.metadata["lastUpdatedAt"]
        if node.error:
            state["error"] = node.error.to_dict()
        return state

    def _build_workflow_snapshot(self, record: RunRecord) -> StartRunRequestWorkflow:
        workflow_dict = record.workflow.to_dict()
        nodes = workflow_dict.get("nodes", [])
        for node_payload in nodes:
            node_id = node_payload.get("id")
            if not node_id:
                continue
            node_state = record.nodes.get(node_id)
            if not node_state:
                continue
            state_payload = self._build_node_state_payload(
                node_state,
                last_updated_at=node_state.finished_at or node_state.started_at,
            )
            node_payload["state"] = state_payload
        return StartRunRequestWorkflow.from_dict(workflow_dict)

    def _format_node(self, node: NodeState) -> Dict[str, Any]:
        node_id = str(node.node_id) if node.node_id is not None else None
        task_id = str(node.task_id) if node.task_id is not None else None
        payload: Dict[str, Any] = {
            "nodeId": node_id,
            "taskId": task_id,
            "status": node.status,
        }
        if node.worker_id:
            payload["workerId"] = node.worker_id
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
            payload["resourceRefs"] = node.resource_refs
        if node.affinity:
            payload["affinity"] = node.affinity
        if node.artifacts:
            payload["artifacts"] = node.artifacts
        if node.result is not None:
            payload["result"] = node.result
        if node.metadata is not None:
            payload["metadata"] = node.metadata
        if node.error:
            payload["error"] = node.error.to_dict()
        state_payload = self._build_node_state_payload(
            node,
            last_updated_at=node.finished_at or node.started_at,
        )
        if state_payload:
            payload["state"] = state_payload
        return payload
    async def create_run(
        self,
        *,
        run_id: str,
        request: StartRunRequest,
        tenant: str,
    ) -> RunRecord:
        async with self._lock:
            workflow = request.workflow
            definition_hash = _compute_definition_hash(workflow)
            record = RunRecord(
                run_id=run_id,
                definition_hash=definition_hash,
                client_id=request.client_id,
                workflow=workflow,
                tenant=tenant,
            )
            self._initialise_nodes(record)
            frames, frames_by_parent = self._build_container_frames(workflow)
            record.frames = frames
            record.frames_by_parent = frames_by_parent
            self._runs[run_id] = record
            snapshot = copy.deepcopy(record)
        await self._publish_run_state(snapshot)
        await self._publish_run_snapshot(snapshot)
        return snapshot

    async def get(self, run_id: str) -> Optional[RunRecord]:
        async with self._lock:
            record = self._runs.get(run_id)
            return copy.deepcopy(record) if record else None

    async def get_by_task(self, task_id: str) -> Optional[RunRecord]:
        async with self._lock:
            for record in self._runs.values():
                if record.task_id == task_id:
                    return copy.deepcopy(record)
                if record.find_node_by_task(task_id):
                    return copy.deepcopy(record)
        return None

    async def get_workflow_with_state(self, run_id: str) -> Optional[StartRunRequestWorkflow]:
        async with self._lock:
            record = self._runs.get(run_id)
            if not record:
                return None
            snapshot = copy.deepcopy(record)
        return self._build_workflow_snapshot(snapshot)

    async def snapshot(self) -> List[RunRecord]:
        async with self._lock:
            return [copy.deepcopy(record) for record in self._runs.values()]

    async def collect_ready_nodes(self, run_id: Optional[str] = None) -> List[DispatchRequest]:
        async with self._lock:
            records: Iterable[RunRecord]
            if run_id:
                record = self._runs.get(run_id)
                records = [record] if record else []
            else:
                records = self._runs.values()
            requests: List[DispatchRequest] = []
            for record in records:
                if not record or record.status in FINAL_STATUSES:
                    continue
                active_frame = self._current_frame(record)
                if active_frame:
                    requests.extend(self._collect_ready_for_frame(record, active_frame))
                else:
                    requests.extend(self._collect_ready_for_record(record))
            return requests

    async def mark_dispatched(
        self,
        run_id: str,
        *,
        worker_id: str,
        task_id: str,
        node_id: str,
        node_type: str,
        package_name: str,
        package_version: str,
        seq_used: int,
        resource_refs: Optional[List[Dict[str, Any]]] = None,
        affinity: Optional[Dict[str, Any]] = None,
        dispatch_id: Optional[str] = None,
        ack_deadline: Optional[datetime] = None,
    ) -> Optional[RunRecord]:
        async with self._lock:
            record = self._runs.get(run_id)
            if not record:
                return None
            if record.status in FINAL_STATUSES:
                return copy.deepcopy(record)
            previous_status = record.status
            timestamp = _utc_now()
            record.status = "running"
            record.started_at = record.started_at or timestamp
            record.worker_id = worker_id
            record.task_id = task_id
            record.node_id = node_id
            record.node_type = node_type
            record.package_name = package_name
            record.package_version = package_version
            record.next_seq = max(record.next_seq, seq_used + 1)
            node_state, frame_state = self._resolve_node_state(
                record,
                node_id=node_id,
                task_id=task_id,
            )
            if not node_state:
                node_state = record.get_node(node_id, task_id=task_id)
                frame_state = None
            node_state.status = "running"
            node_state.worker_id = worker_id
            node_state.started_at = timestamp
            node_state.finished_at = None
            node_state.seq = seq_used
            if resource_refs is not None:
                node_state.resource_refs = copy.deepcopy(resource_refs)
            if affinity is not None:
                node_state.affinity = copy.deepcopy(affinity)
            node_state.error = None
            node_state.enqueued = False
            node_state.pending_ack = dispatch_id is not None
            node_state.dispatch_id = dispatch_id
            node_state.ack_deadline = ack_deadline
            record.refresh_rollup()
            new_status = record.status
            if new_status in FINAL_STATUSES:
                self._pending_next_requests = {
                    req_id: (r_id, worker_id, deadline, node_id, middleware_id, target_task_id)
                    for req_id, (r_id, worker_id, deadline, node_id, middleware_id, target_task_id) in self._pending_next_requests.items()
                    if r_id != record.run_id
                }
            record_snapshot = copy.deepcopy(record)
            node_snapshot = copy.deepcopy(node_state)
        tasks = []
        tasks.append(self._publish_node_state(record_snapshot, node_snapshot))
        if new_status != previous_status:
            tasks.append(self._publish_run_state(record_snapshot))
        tasks.append(self._publish_run_snapshot(record_snapshot))
        await asyncio.gather(*tasks)
        return record_snapshot

    async def mark_acknowledged(
        self,
        run_id: str,
        *,
        node_id: str,
        dispatch_id: str,
    ) -> Optional[RunRecord]:
        async with self._lock:
            record = self._runs.get(run_id)
            if not record:
                return None
            if record.status in FINAL_STATUSES:
                return copy.deepcopy(record)
            node_state, frame_state = self._find_node_by_dispatch(record, dispatch_id)
            if not node_state or node_state.node_id != node_id:
                return copy.deepcopy(record)
            previous_status = record.status
            node_state.pending_ack = False
            node_state.ack_deadline = None
            record.refresh_rollup()
            record_snapshot = copy.deepcopy(record)
            node_snapshot = copy.deepcopy(node_state)
        tasks = []
        tasks.append(self._publish_node_state(record_snapshot, node_snapshot))
        if record_snapshot.status != previous_status:
            tasks.append(self._publish_run_state(record_snapshot))
        tasks.append(self._publish_run_snapshot(record_snapshot))
        await asyncio.gather(*tasks)
        return record_snapshot

    async def cancel_run(self, run_id: str) -> tuple[Optional[RunRecord], List[Tuple[str, str, str, Optional[str], Optional[str]]]]:
        def _cancel_nodes(nodes: Dict[str, NodeState], timestamp: datetime) -> None:
            for node in nodes.values():
                if node.status in FINAL_STATUSES:
                    continue
                node.status = "cancelled"
                node.enqueued = False
                node.pending_dependencies = 0
                node.pending_ack = False
                node.dispatch_id = None
                node.ack_deadline = None
                node.finished_at = timestamp

        async with self._lock:
            record = self._runs.get(run_id)
            if not record:
                return None, []
            if record.status in FINAL_STATUSES:
                return copy.deepcopy(record), []
            timestamp = _utc_now()
            _cancel_nodes(record.nodes, timestamp)
            for frame in record.active_frames.values():
                _cancel_nodes(frame.nodes, timestamp)
            record.active_frames.clear()
            record.frame_stack.clear()
            record.status = "cancelled"
            record.finished_at = timestamp
            cancelled_next: List[Tuple[str, str, str, Optional[str], Optional[str]]] = []
            # drop pending middleware next requests for this run and surface worker targets
            remaining_next: Dict[str, Tuple[str, Optional[str], Optional[datetime], Optional[str], Optional[str], Optional[str]]] = {}
            for req_id, (r_id, worker_id, deadline, node_id, middleware_id, target_task_id) in self._pending_next_requests.items():
                if r_id == run_id and worker_id:
                    cancelled_next.append((req_id, worker_id, r_id, node_id, middleware_id))
                    continue
                if r_id == run_id:
                    continue
                remaining_next[req_id] = (r_id, worker_id, deadline, node_id, middleware_id, target_task_id)
            self._pending_next_requests = remaining_next
            record.refresh_rollup()
            record.status = "cancelled"
            record_snapshot = copy.deepcopy(record)

        await asyncio.gather(
            self._publish_run_state(record_snapshot),
            self._publish_run_snapshot(record_snapshot),
        )
        return record_snapshot, cancelled_next

    async def reset_after_ack_timeout(
        self,
        run_id: str,
        *,
        node_id: str,
        dispatch_id: str,
    ) -> Optional[RunRecord]:
        async with self._lock:
            record = self._runs.get(run_id)
            if not record:
                return None
            if record.status in FINAL_STATUSES:
                return copy.deepcopy(record)
            node_state, frame_state = self._find_node_by_dispatch(record, dispatch_id)
            if not node_state or node_state.node_id != node_id:
                return copy.deepcopy(record)
            previous_status = record.status
            previous_worker = node_state.worker_id
            previous_node_type = node_state.node_type
            previous_package_name = node_state.package_name
            previous_package_version = node_state.package_version
            previous_task_id = node_state.task_id

            node_state.status = "queued"
            node_state.worker_id = None
            node_state.started_at = None
            node_state.finished_at = None
            node_state.seq = None
            node_state.pending_ack = False
            node_state.dispatch_id = None
            node_state.ack_deadline = None
            node_state.enqueued = True
            node_state.error = None
            if record.node_id == node_id:
                record.node_id = None
            if record.task_id == previous_task_id:
                record.task_id = None
            if record.node_type == previous_node_type:
                record.node_type = None
            if record.worker_id == previous_worker:
                record.worker_id = None
            if record.package_name == previous_package_name:
                record.package_name = None
            if record.package_version == previous_package_version:
                record.package_version = None
            record.refresh_rollup()
            new_status = record.status
            record_snapshot = copy.deepcopy(record)
            node_snapshot = copy.deepcopy(node_state)
        tasks = []
        tasks.append(self._publish_node_state(record_snapshot, node_snapshot))
        if new_status != previous_status:
            tasks.append(self._publish_run_state(record_snapshot))
        tasks.append(self._publish_run_snapshot(record_snapshot))
        await asyncio.gather(*tasks)
        return record_snapshot

    async def record_result(
        self,
        run_id: str,
        payload: ws_result.ResultPayload,
    ) -> tuple[Optional[RunRecord], List[DispatchRequest], List[Tuple[Optional[str], NextResponsePayload]]]:
        async with self._lock:
            record = self._runs.get(run_id)
            if not record:
                return None, [], []
            if record.status in FINAL_STATUSES:
                return copy.deepcopy(record), [], []
            previous_status = record.status
            status = _normalise_status(payload.status.value)
            node_state, frame_state = self._resolve_node_state(
                record,
                node_id=None,
                task_id=payload.task_id,
            )
            if not node_state:
                node_state = record.get_node(payload.task_id, task_id=payload.task_id)
                frame_state = None
            timestamp = _utc_now()
            node_state.status = status
            node_state.finished_at = timestamp
            node_state.result = payload.result
            # Preserve existing metadata (role/host info) when merging adapter metadata
            existing_meta = node_state.metadata or {}
            incoming_meta = copy.deepcopy(payload.metadata) if payload.metadata else {}
            merged_meta = {**existing_meta, **incoming_meta}
            node_state.metadata = merged_meta if merged_meta else None
            node_state.artifacts = [
                artifact.model_dump(exclude_none=True)
                for artifact in (payload.artifacts or [])
            ]
            node_state.error = None
            node_state.enqueued = False
            record.duration_ms = payload.duration_ms
            record.result_payload = payload.result
            if payload.error:
                node_error = ListRuns200ResponseItemsInnerError(
                    code=payload.error.code,
                    message=payload.error.message,
                    details={"remediation": payload.error.remediation} if payload.error.remediation else None,
                )
                node_state.error = node_error
                record.error = node_error
            elif status == "succeeded":
                node_state.error = None
                record.error = None

            ready: List[DispatchRequest] = []
            next_responses: List[Tuple[Optional[str], NextResponsePayload]] = []
            # Host nodes with middleware chains keep looping; do not release dependents or finalize yet.
            if not self._is_host_with_middleware(node_state):
                if status == "succeeded":
                    if frame_state:
                        self._apply_frame_edge_bindings(frame_state, node_state)
                    else:
                        self._apply_edge_bindings(record, node_state)
                    self._release_dependents(record, node_state, frame_state, ready)
            else:
                # Allow the host to be dispatched again by middleware.next()
                node_state.status = "queued"
                node_state.enqueued = False
                node_state.pending_dependencies = 0
                node_state.chain_blocked = True

            # Middleware completion finalises the host and releases its dependents.
            host_snapshot: Optional[NodeState] = None
            if self._is_middleware_node(node_state):
                # Keep middleware reusable for subsequent next() invocations if it succeeded.
                if status == "succeeded":
                    node_state.status = "queued"
                    node_state.enqueued = False
                    node_state.pending_dependencies = 0
                node_state.chain_blocked = True

                host_id = node_state.metadata.get("host_node_id") if node_state.metadata else None
                if host_id:
                    host_state, host_frame = self._resolve_node_state(record, node_id=str(host_id), task_id=None)
                    if host_state:
                        # Surface middleware outputs onto the host payload so downstream bindings can consume them.
                        self._apply_middleware_output_bindings(host_state, node_state)
                        chain_index = node_state.metadata.get("chain_index") if node_state.metadata else None
                        chain_len = len(host_state.middlewares) if host_state.middlewares else 0
                        # Only the outermost (first) middleware closes the U-shape and finalises the host.
                        is_outermost = chain_index is None or chain_index == 0
                        if is_outermost:
                            host_state.status = status
                            host_state.finished_at = timestamp
                            # Keep host data isolated; middleware data remains on the middleware node
                            host_state.result = host_state.result
                            host_state.metadata = host_state.metadata
                            host_state.artifacts = host_state.artifacts
                            host_state.error = host_state.error
                            host_state.enqueued = False
                            host_state.pending_dependencies = 0
                            if status == "succeeded":
                                if host_frame:
                                    self._apply_frame_edge_bindings(host_frame, host_state)
                                else:
                                    self._apply_edge_bindings(record, host_state)
                                self._release_dependents(record, host_state, host_frame, ready)
                        host_snapshot = copy.deepcopy(host_state)

            container_snapshot: Optional[NodeState] = None
            if frame_state:
                frame_ready, container_node, frame_next_responses = self._complete_frame_if_needed(record, frame_state)
                ready.extend(frame_ready)
                next_responses.extend(frame_next_responses)
                if container_node and frame_state.parent_frame_id is None:
                    container_snapshot = copy.deepcopy(container_node)

            # Resolve pending middleware.next responses targeting this task
            next_responses.extend(self._finalise_pending_next(payload, node_state, status=status))

            record.refresh_rollup()
            new_status = record.status
            record_snapshot = copy.deepcopy(record)
            node_snapshot = copy.deepcopy(node_state)
        tasks = [
            self._publish_node_state(record_snapshot, node_snapshot),
            self._publish_node_snapshot(
                record_snapshot,
                node_snapshot,
                complete=status in FINAL_STATUSES,
            ),
        ]
        if host_snapshot:
            tasks.append(
                self._publish_node_snapshot(
                    record_snapshot,
                    host_snapshot,
                    complete=status in FINAL_STATUSES,
                )
            )
        if container_snapshot:
            tasks.extend(
                [
                    self._publish_node_state(record_snapshot, container_snapshot),
                    self._publish_node_snapshot(
                        record_snapshot,
                        container_snapshot,
                        complete=True,
                    ),
                ]
            )
        if new_status != previous_status:
            tasks.append(self._publish_run_state(record_snapshot))
        tasks.append(self._publish_run_snapshot(record_snapshot))
        await asyncio.gather(*tasks)
        return record_snapshot, ready, next_responses

    async def record_feedback(
        self,
        payload: FeedbackPayload,
    ) -> None:
        async with self._lock:
            record = self._runs.get(payload.run_id)
            if not record:
                return
            node_state, frame_state = self._resolve_node_state(
                record,
                node_id=None,
                task_id=payload.task_id,
            )
            if not node_state:
                node_state = record.get_node(payload.task_id, task_id=payload.task_id)
                frame_state = None
            metadata = node_state.metadata or {}
            node_state.metadata = metadata
            changed_state = False
            now = _utc_now()
            metadata["lastUpdatedAt"] = now.isoformat()
            result_deltas: List[Dict[str, Any]] = []
            if payload.stage:
                metadata["stage"] = payload.stage
                changed_state = True
            if payload.progress is not None:
                metadata["progress"] = payload.progress
                changed_state = True
            if payload.message:
                metadata["message"] = payload.message
                changed_state = True
            incoming_metadata = payload.metadata or {}
            incoming_results = incoming_metadata.get("results")
            if incoming_results is None and "summary" in incoming_metadata:
                incoming_results = {"summary": incoming_metadata.get("summary")}
            for key, value in incoming_metadata.items():
                if key == "results":
                    continue
                if value is None:
                    if key in metadata:
                        metadata.pop(key, None)
                        changed_state = True
                else:
                    copied = copy.deepcopy(value) if isinstance(value, (dict, list)) else value
                    if metadata.get(key) != copied:
                        metadata[key] = copied
                        changed_state = True
            if isinstance(incoming_results, dict):
                if not isinstance(node_state.result, dict):
                    node_state.result = {}
                result_changes = _merge_result_updates(node_state.result, incoming_results)
                if result_changes:
                    changed_state = True
                    seq_counter = int(metadata.get("resultSequence", 0))
                    for change in result_changes:
                        seq_counter += 1
                        change["sequence"] = seq_counter
                        change["revision"] = node_state.seq or 0
                    metadata["resultSequence"] = seq_counter
                    result_deltas.extend(result_changes)
            if payload.metrics:
                metrics = metadata.setdefault("metrics", {})
                metrics.update(payload.metrics)
                changed_state = True

            chunk_events: List[Dict[str, Any]] = []
            if payload.chunks:
                feedback_meta: Dict[str, Any] = metadata.setdefault("feedback", {})
                seq = int(feedback_meta.get("sequence", 0))
                revision = node_state.seq or 0
                for chunk in payload.chunks:
                    seq += 1
                    chunk_dict = chunk.model_dump(exclude_none=True)
                    chunk_events.append(
                        {
                            "revision": revision,
                            "sequence": seq,
                            "chunk": chunk_dict,
                        }
                    )
                feedback_meta["sequence"] = seq
                changed_state = True

            record_snapshot: Optional[RunRecord] = None
            node_snapshot: Optional[NodeState] = None
            if changed_state or chunk_events:
                record_snapshot = copy.deepcopy(record)
                node_snapshot = record_snapshot.nodes.get(node_state.node_id)
                if node_snapshot is None:
                    node_snapshot = copy.deepcopy(node_state)
            publish_node_state = bool(changed_state and record_snapshot and node_snapshot)
        tasks: List[asyncio.Future[Any]] = []
        if publish_node_state:
            tasks.append(self._publish_node_state(record_snapshot, node_snapshot))
            tasks.append(
                self._publish_node_snapshot(
                    record_snapshot,
                    node_snapshot,
                    complete=False,
                )
            )
        if chunk_events and record_snapshot:
            node_for_delta = node_snapshot or record_snapshot.nodes.get(node_state.node_id) or node_state
            for event in chunk_events:
                chunk = event["chunk"]
                channel = chunk.get("channel") or "log"
                mime_type = chunk.get("mime_type")
                payload_body: Dict[str, Any] = {}
                if "text" in chunk and chunk["text"] is not None:
                    payload_body["text"] = chunk["text"]
                if "data_base64" in chunk and chunk["data_base64"] is not None:
                    payload_body["data"] = chunk["data_base64"]
                if mime_type:
                    payload_body["mimeType"] = mime_type
                chunk_meta = {"channel": channel}
                if chunk.get("metadata"):
                    chunk_meta["metadata"] = chunk["metadata"]
                terminal = False
                if isinstance(chunk.get("metadata"), dict):
                    terminal = bool(chunk["metadata"].get("terminal"))
                tasks.append(
                    self._publish_node_result_delta(
                        record_snapshot,
                        node_for_delta or node_state,
                        revision=event["revision"],
                        sequence=event["sequence"],
                        operation="append",
                        path=f"/channels/{channel}" if channel else None,
                        payload=payload_body or None,
                        chunk_meta=chunk_meta or None,
                        terminal=terminal,
                    )
                )
        if result_deltas and record_snapshot:
            node_for_delta = node_snapshot or record_snapshot.nodes.get(node_state.node_id) or node_state
            for delta in result_deltas:
                operation = delta["operation"]
                value = delta.get("value")
                payload_body = {"value": value} if operation != "remove" else None
                tasks.append(
                    self._publish_node_result_delta(
                        record_snapshot,
                        node_for_delta,
                        revision=delta["revision"],
                        sequence=delta["sequence"],
                        operation=operation,
                        path=delta["path"],
                        payload=payload_body,
                        chunk_meta=None,
                        terminal=False,
                    )
                )
        if tasks:
            await asyncio.gather(*tasks)

    async def handle_next_request(
        self,
        payload: NextRequestPayload,
        *,
        worker_id: Optional[str],
    ) -> Tuple[List[DispatchRequest], Optional[str]]:
        async with self._lock:
            record = self._runs.get(payload.run_id)
            if not record or record.status in FINAL_STATUSES:
                return [], "next_run_finalised"
            if payload.request_id in self._pending_next_requests:
                return [], "next_duplicate"

            host_node_id = None
            chain: Optional[List[str]] = None
            for node in record.nodes.values():
                chain_ids = getattr(node, "middlewares", []) or []
                if payload.middleware_id in chain_ids:
                    host_node_id = node.node_id
                    chain = chain_ids
                    break
            if not chain:
                return [], "next_no_chain"

            try:
                current_index = (
                    payload.chain_index if payload.chain_index is not None else chain.index(payload.middleware_id)
                )
            except ValueError:
                return [], "next_invalid_chain"
            target_index = current_index + 1
            if target_index < len(chain):
                target_node_id = chain[target_index]
                target_chain_index = target_index
            else:
                target_node_id = host_node_id
                target_chain_index = None

            node_state, frame_state = self._resolve_node_state(
                record,
                node_id=target_node_id,
                task_id=None,
            )
            if not node_state:
                return [], "next_target_not_ready"

            # Middleware chains may need to re-dispatch nodes that previously finished; reset lightweight state.
            if self._is_middleware_node(node_state) or self._is_host_with_middleware(node_state):
                if node_state.status in FINAL_STATUSES:
                    node_state.status = "queued"
            node_state.enqueued = False

            if node_state.status != "queued" or node_state.enqueued:
                return [], "next_target_not_ready"
            if node_state.pending_dependencies != 0:
                return [], "next_target_not_ready"
            node_state.chain_blocked = False

            parent_frame_id = frame_state.frame_id if frame_state else None
            if self._is_container_node(node_state):
                frame_ready = self._start_container_execution(
                    record,
                    node_state,
                    parent_frame_id=parent_frame_id,
                )
                deadline = None
                if payload.timeout_ms and payload.timeout_ms > 0:
                    deadline = _utc_now() + timedelta(milliseconds=payload.timeout_ms)
                self._pending_next_requests[payload.request_id] = (
                    record.run_id,
                    worker_id,
                    deadline,
                    payload.node_id,
                    payload.middleware_id,
                    node_state.task_id,
                )
                return frame_ready, None

            dispatch = self._build_dispatch_request(
                record,
                node_state,
                host_node_id=host_node_id,
                middleware_chain=chain,
                chain_index=target_chain_index,
            )
            deadline = None
            if payload.timeout_ms and payload.timeout_ms > 0:
                deadline = _utc_now() + timedelta(milliseconds=payload.timeout_ms)
            self._pending_next_requests[payload.request_id] = (
                record.run_id,
                worker_id,
                deadline,
                payload.node_id,
                payload.middleware_id,
                node_state.task_id,
            )
            record_snapshot = copy.deepcopy(record)
            node_snapshot = copy.deepcopy(node_state)
        await asyncio.gather(
            self._publish_node_state(record_snapshot, node_snapshot),
            self._publish_run_snapshot(record_snapshot),
        )
        return [dispatch], None

    async def resolve_next_response_worker(self, request_id: str) -> Optional[str]:
        async with self._lock:
            entry = self._pending_next_requests.pop(request_id, None)
            if not entry:
                return None
            _, worker_id, deadline, _, _, _ = entry
            if deadline and _utc_now() > deadline:
                return None
            return worker_id

    async def collect_expired_next_requests(self) -> List[Tuple[str, str, str, Optional[str], Optional[str]]]:
        async with self._lock:
            now = _utc_now()
            expired: List[Tuple[str, str, str, Optional[str], Optional[str]]] = []
            remaining: Dict[str, Tuple[str, Optional[str], Optional[datetime], Optional[str], Optional[str], Optional[str]]] = {}
            for req_id, (run_id, worker_id, deadline, node_id, middleware_id, target_task_id) in self._pending_next_requests.items():
                if deadline and now > deadline:
                    if worker_id:
                        expired.append((req_id, worker_id, run_id, node_id, middleware_id))
                else:
                    remaining[req_id] = (run_id, worker_id, deadline, node_id, middleware_id, target_task_id)
            self._pending_next_requests = remaining
            return expired

    def get_next_error_message(self, code: str) -> str:
        return self._next_error_messages.get(code, "next request rejected")

    async def record_command_error(
        self,
        payload: ErrorPayload,
        *,
        run_id: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> tuple[Optional[RunRecord], List[DispatchRequest]]:
        async with self._lock:
            record = None
            if run_id:
                record = self._runs.get(run_id)
            if not record and task_id:
                record = next(
                    (candidate for candidate in self._runs.values() if candidate.task_id == task_id),
                    None,
                )
            if not record:
                return None, []
            if record.status in FINAL_STATUSES:
                return copy.deepcopy(record), []
            previous_status = record.status
            details = payload.context.details if payload.context and payload.context.details else None
            error = ListRuns200ResponseItemsInnerError(
                code=payload.code,
                message=payload.message,
                details=details,
            )
            record.error = error
            record.status = "failed"
            node_state: Optional[NodeState] = None
            frame_state: Optional[FrameRuntimeState] = None
            if task_id:
                node_state, frame_state = self._resolve_node_state(
                    record,
                    node_id=None,
                    task_id=task_id,
                )
            if not node_state and record.node_id:
                node_state, frame_state = self._resolve_node_state(
                    record,
                    node_id=record.node_id,
                    task_id=None,
                )
            node_snapshot = None
            container_snapshot = None
            ready: List[DispatchRequest] = []
            if node_state:
                node_state.status = "failed"
                node_state.finished_at = _utc_now()
                node_state.error = error
                node_state.enqueued = False
                node_state.pending_ack = False
                node_state.dispatch_id = None
                node_state.ack_deadline = None
                node_state.worker_id = None
                if frame_state:
                    frame_ready, container_node, _ = self._complete_frame_if_needed(record, frame_state)
                    ready.extend(frame_ready)
                    if container_node and frame_state.parent_frame_id is None:
                        container_snapshot = copy.deepcopy(container_node)
                node_snapshot = copy.deepcopy(node_state)
            record.refresh_rollup()
            record_snapshot = copy.deepcopy(record)
        tasks = []
        if node_snapshot is not None:
            tasks.append(self._publish_node_state(record_snapshot, node_snapshot))
        if container_snapshot:
            tasks.append(self._publish_node_state(record_snapshot, container_snapshot))
        if record_snapshot.status != previous_status:
            tasks.append(self._publish_run_state(record_snapshot))
        tasks.append(self._publish_run_snapshot(record_snapshot))
        if tasks:
            await asyncio.gather(*tasks)
        return record_snapshot, ready

    async def to_list_response(
        self,
        *,
        limit: int,
        cursor: Optional[str],
        status: Optional[str],
        client_id: Optional[str],
    ) -> ListRuns200Response:
        runs = await self.snapshot()
        runs.sort(key=lambda r: r.created_at)
        filtered: Iterable[RunRecord] = runs
        if status:
            filtered = [r for r in filtered if r.status == status]
        if client_id:
            filtered = [r for r in filtered if r.client_id == client_id]
        filtered_list = list(filtered)

        start_index = 0
        if cursor:
            for idx, candidate in enumerate(filtered_list):
                if candidate.run_id == cursor:
                    start_index = idx + 1
                    break

        window = filtered_list[start_index : start_index + limit]
        items = [r.to_summary() for r in window]
        next_cursor = None
        if start_index + len(window) < len(filtered_list):
            next_cursor = filtered_list[start_index + len(window) - 1].run_id
        return ListRuns200Response(items=items, nextCursor=next_cursor)

    def _resolve_middleware_chain(
        self,
        record: RunRecord,
        node: NodeState,
    ) -> Optional[Tuple[str, List[str], int]]:
        target_id = node.node_id

        def _scan(nodes: Dict[str, NodeState]) -> Optional[Tuple[str, List[str], int]]:
            for candidate in nodes.values():
                chain = getattr(candidate, "middlewares", []) or []
                if target_id in chain:
                    try:
                        return candidate.node_id, chain, chain.index(target_id)
                    except ValueError:
                        continue
            return None

        if node.frame_id and node.frame_id in record.active_frames:
            frame = record.active_frames.get(node.frame_id)
            if frame:
                found = _scan(frame.nodes)
                if found:
                    return found
        found = _scan(record.nodes)
        if found:
            return found
        for frame in record.active_frames.values():
            found = _scan(frame.nodes)
            if found:
                return found
        return None

    def _build_dispatch_request_for_node(self, record: RunRecord, node: NodeState) -> DispatchRequest:
        host_node_id = None
        middleware_chain = None
        chain_index = None
        chain_info = self._resolve_middleware_chain(record, node)
        if chain_info:
            host_node_id, middleware_chain, chain_index = chain_info
        return self._build_dispatch_request(
            record,
            node,
            host_node_id=host_node_id,
            middleware_chain=middleware_chain,
            chain_index=chain_index,
        )

    def _initialise_nodes(self, record: RunRecord) -> None:
        nodes: Dict[str, NodeState] = {}
        def _add_dependency(source_state: NodeState, target_state: NodeState) -> None:
            if target_state.node_id not in source_state.dependencies:
                source_state.dependencies.append(target_state.node_id)
                source_state.pending_dependencies += 1
            if source_state.node_id not in target_state.dependents:
                target_state.dependents.append(source_state.node_id)

        def _propagate_host_dependencies_to_first_middleware() -> None:
            """Ensure the first middleware in a chain inherits the host's upstream dependencies."""
            for node in record.workflow.nodes or []:
                mw_ids, _ = _extract_middleware_entries(getattr(node, "middlewares", []) or [])
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
            middleware_ids, middleware_defs = _extract_middleware_entries(getattr(node, "middlewares", []) or [])
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

        # First middleware waits for the same upstream dependencies as its host
        _propagate_host_dependencies_to_first_middleware()
        _wire_middleware_chain_dependencies()

        record.nodes = nodes
        record.scope_index = WorkflowScopeIndex(record.workflow)
        record.edge_bindings = self._build_edge_bindings(record)

    def _build_container_frames(
        self,
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
                            _mw_ids, mw_defs = _extract_middleware_entries(mws)
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
                child_subgraph_id = _get_node_subgraph_id(child)
                if child.type == "workflow.container" and child_subgraph_id:
                    walk(str(child.id), str(child_subgraph_id), frame_alias_chain, frame_id)

        task_index: Dict[str, NodeState] = {}
        for node in workflow.nodes or []:
            subgraph_id = _get_node_subgraph_id(node)
            if node.type == "workflow.container" and subgraph_id:
                walk(str(node.id), str(subgraph_id), (str(workflow.id) or "root",), None)

        return frames, frames_by_parent

    def _initialise_frame_runtime(self, record: RunRecord, frame: FrameDefinition) -> FrameRuntimeState:
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
                mw_ids, _ = _extract_middleware_entries(getattr(node, "middlewares", []) or [])
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
            middleware_ids, middleware_defs = _extract_middleware_entries(getattr(node, "middlewares", []) or [])
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
        edge_bindings = self._build_edge_bindings_for_workflow(workflow, scope_index)
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

    def _activate_frame(self, record: RunRecord, frame: FrameDefinition) -> FrameRuntimeState:
        frame_state = self._initialise_frame_runtime(record, frame)
        record.active_frames[frame.frame_id] = frame_state
        record.frame_stack.append(frame.frame_id)
        return frame_state

    def _pop_frame(self, record: RunRecord, frame_id: str) -> None:
        record.active_frames.pop(frame_id, None)
        if record.frame_stack and record.frame_stack[-1] == frame_id:
            record.frame_stack.pop()
            return
        if frame_id in record.frame_stack:
            record.frame_stack = [fid for fid in record.frame_stack if fid != frame_id]

    def _current_frame(self, record: RunRecord) -> Optional[FrameRuntimeState]:
        if not record.frame_stack:
            return None
        return record.active_frames.get(record.frame_stack[-1])

    def _resolve_node_state(
        self,
        record: RunRecord,
        *,
        node_id: Optional[str],
        task_id: Optional[str],
    ) -> Tuple[Optional[NodeState], Optional[FrameRuntimeState]]:
        if task_id:
            root_candidate = record.task_index.get(task_id)
            if root_candidate:
                return root_candidate, None
            for frame_id in reversed(record.frame_stack):
                frame = record.active_frames.get(frame_id)
                if not frame:
                    continue
                candidate = frame.task_index.get(task_id)
                if candidate:
                    return candidate, frame
            for frame in record.active_frames.values():
                candidate = frame.task_index.get(task_id)
                if candidate:
                    return candidate, frame
        if node_id:
            root_candidate = record.nodes.get(node_id)
            if root_candidate:
                return root_candidate, None
            for frame_id in reversed(record.frame_stack):
                frame = record.active_frames.get(frame_id)
                if not frame:
                    continue
                candidate = frame.nodes.get(node_id)
                if candidate:
                    return candidate, frame
            for frame in record.active_frames.values():
                candidate = frame.nodes.get(node_id)
                if candidate:
                    return candidate, frame
        return None, None

    def _find_node_by_dispatch(
        self,
        record: RunRecord,
        dispatch_id: str,
    ) -> Tuple[Optional[NodeState], Optional[FrameRuntimeState]]:
        for node in record.nodes.values():
            if node.dispatch_id == dispatch_id:
                return node, None
        for frame in record.active_frames.values():
            for node in frame.nodes.values():
                if node.dispatch_id == dispatch_id:
                    return node, frame
        return None, None

    def _find_frame_for_container(
        self,
        record: RunRecord,
        *,
        container_node_id: str,
        parent_frame_id: Optional[str],
    ) -> Optional[FrameDefinition]:
        if not record.frames_by_parent:
            return None
        return record.frames_by_parent.get((parent_frame_id, container_node_id))

    def _get_parent_graph(
        self,
        record: RunRecord,
        parent_frame_id: Optional[str],
    ) -> Tuple[Dict[str, NodeState], Optional[FrameRuntimeState]]:
        if parent_frame_id is None:
            return record.nodes, None
        parent_frame = record.active_frames.get(parent_frame_id)
        if parent_frame:
            return parent_frame.nodes, parent_frame
        return record.nodes, None

    def _complete_frame_if_needed(
        self,
        record: RunRecord,
        frame: FrameRuntimeState,
    ) -> Tuple[List[DispatchRequest], Optional[NodeState], List[Tuple[Optional[str], NextResponsePayload]]]:
        nodes = list(frame.nodes.values())
        failed = any(node.status == "failed" for node in nodes)
        terminal = all(node.status in FINAL_STATUSES for node in nodes)
        if not failed and not terminal:
            return [], None, []

        if failed:
            for node in nodes:
                if node.status not in FINAL_STATUSES:
                    node.status = "cancelled"
                    node.enqueued = False

        parent_nodes, _ = self._get_parent_graph(record, frame.parent_frame_id)
        container_node = parent_nodes.get(frame.container_node_id)
        if not container_node:
            self._pop_frame(record, frame.frame_id)
            return [], None

        now = _utc_now()
        container_node.finished_at = now
        container_node.enqueued = False
        container_node.pending_ack = False
        container_node.dispatch_id = None
        container_node.ack_deadline = None
        container_node.worker_id = None
        container_node.error = None
        if container_node.started_at is None:
            container_node.started_at = frame.started_at or now
        frame.finished_at = now
        frame.status = "failed" if failed else "succeeded"
        if failed:
            container_node.status = "failed"
            failing_error = next((node.error for node in nodes if node.error), None)
            container_node.error = failing_error
        else:
            container_node.status = "succeeded"

        if container_node.result is None or not isinstance(container_node.result, dict):
            container_node.result = {}

        record.completed_frames[frame.frame_id] = {
            node_id: copy.deepcopy(node_state) for node_id, node_state in frame.nodes.items()
        }
        self._pop_frame(record, frame.frame_id)
        ready: List[DispatchRequest] = []
        next_responses: List[Tuple[Optional[str], NextResponsePayload]] = []
        pending_next_to_clear = [
            (req_id, worker_id, run_id, node_id, middleware_id)
            for req_id, (run_id, worker_id, deadline, node_id, middleware_id, target_task_id)
            in self._pending_next_requests.items()
            if target_task_id == container_node.task_id
        ]
        for req_id, worker_id, run_id, node_id, middleware_id in pending_next_to_clear:
            self._pending_next_requests.pop(req_id, None)
            err_body = None
            if container_node.error:
                err_body = {"code": container_node.error.code, "message": container_node.error.message}
            elif failed:
                err_body = {"code": "next_failed", "message": f"target {container_node.node_id} status failed"}
            resp = NextResponsePayload(
                requestId=req_id,
                runId=run_id,
                nodeId=node_id or "",
                middlewareId=middleware_id or "",
                result=container_node.result,
                error=err_body,
            )
            next_responses.append((worker_id, resp))
        # When the container has middlewares, the execution unit isn't finished yet; let the outermost middleware finalise and release dependents.
        if self._is_host_with_middleware(container_node):
            return ready, container_node, next_responses
        for dependent_id in container_node.dependents:
            dependent = parent_nodes.get(dependent_id)
            if not dependent or dependent.status != "queued":
                continue
            if dependent.pending_dependencies > 0:
                dependent.pending_dependencies -= 1
            if getattr(dependent, "chain_blocked", False):
                continue
            if dependent.pending_dependencies == 0 and not dependent.enqueued:
                if dependent.middlewares:
                    continue
                role = dependent.metadata.get("role") if dependent.metadata else None
                if role == "middleware":
                    chain_index = dependent.metadata.get("chain_index") if dependent.metadata else None
                    if chain_index is not None and chain_index > 0:
                        continue
                ready.append(self._build_dispatch_request_for_node(record, dependent))
        return ready, container_node, next_responses

    def _collect_ready_for_record(self, record: RunRecord) -> List[DispatchRequest]:
        ready: List[DispatchRequest] = []
        for node in record.nodes.values():
            if self._is_container_node(node):
                if not self._is_container_ready(node):
                    continue
                frame_ready = self._start_container_execution(
                    record,
                    node,
                    parent_frame_id=None,
                )
                ready.extend(frame_ready)
                continue
            if not self._should_auto_dispatch(node):
                continue
            ready.append(self._build_dispatch_request_for_node(record, node))
        return ready

    def _collect_ready_for_frame(self, record: RunRecord, frame: FrameRuntimeState) -> List[DispatchRequest]:
        ready: List[DispatchRequest] = []
        for node in frame.nodes.values():
            if self._is_container_node(node):
                if not self._is_container_ready(node):
                    continue
                frame_ready = self._start_container_execution(
                    record,
                    node,
                    parent_frame_id=frame.frame_id,
                )
                ready.extend(frame_ready)
                continue
            if not self._should_auto_dispatch(node):
                continue
            ready.append(self._build_dispatch_request_for_node(record, node))
        return ready

    def _start_container_execution(
        self,
        record: RunRecord,
        container_node: NodeState,
        *,
        parent_frame_id: Optional[str],
    ) -> List[DispatchRequest]:
        frame_definition = self._find_frame_for_container(
            record,
            container_node_id=container_node.node_id,
            parent_frame_id=parent_frame_id,
        )
        if not frame_definition:
            frames, frames_by_parent = self._build_container_frames(record.workflow)
            record.frames = frames
            record.frames_by_parent = frames_by_parent
            frame_definition = self._find_frame_for_container(
                record,
                container_node_id=container_node.node_id,
                parent_frame_id=parent_frame_id,
            )
        if not frame_definition:
            LOGGER.error(
                "Container node %s missing subgraph frame (parent_frame=%s)",
                container_node.node_id,
                parent_frame_id,
            )
            container_node.status = "failed"
            container_node.enqueued = True
            container_node.finished_at = _utc_now()
            return []

        if container_node.started_at is None:
            container_node.started_at = _utc_now()
        container_node.status = "running"
        container_node.enqueued = True
        container_node.metadata = container_node.metadata or {}
        container_node.metadata["frameId"] = frame_definition.frame_id

        frame_state = self._activate_frame(record, frame_definition)
        return self._collect_ready_for_frame(record, frame_state)

    def _build_dispatch_request(
        self,
        record: RunRecord,
        node: NodeState,
        *,
        host_node_id: Optional[str] = None,
        middleware_chain: Optional[List[str]] = None,
        chain_index: Optional[int] = None,
    ) -> DispatchRequest:
        node.enqueued = True
        resource_refs = copy.deepcopy(node.resource_refs)
        affinity = copy.deepcopy(node.affinity) if node.affinity else None
        worker_ids = {
            ref.get("workerId") or ref.get("worker_id")
            for ref in resource_refs
            if ref.get("workerId") or ref.get("worker_id")
        }
        preferred_worker_id = None
        if len(worker_ids) == 1:
            preferred_worker_id = next(iter(worker_ids))
        seq = record.next_seq
        record.next_seq = seq + 1
        return DispatchRequest(
            run_id=record.run_id,
            tenant=record.tenant,
            node_id=node.node_id,
            task_id=node.task_id,
            node_type=node.node_type,
            package_name=node.package_name,
            package_version=node.package_version,
            parameters=copy.deepcopy(node.parameters),
            resource_refs=resource_refs,
            affinity=affinity,
            concurrency_key=node.concurrency_key or f"{record.run_id}:{node.node_id}",
            seq=seq,
            preferred_worker_id=preferred_worker_id,
            host_node_id=host_node_id,
            middleware_chain=middleware_chain,
            chain_index=chain_index,
        )

    def _build_edge_bindings(self, record: RunRecord) -> Dict[str, List[EdgeBinding]]:
        return self._build_edge_bindings_for_workflow(record.workflow, record.scope_index)

    def _build_edge_bindings_for_workflow(
        self,
        workflow: StartRunRequestWorkflow,
        scope_index: Optional[WorkflowScopeIndex],
    ) -> Dict[str, List[EdgeBinding]]:
        workflow_nodes = {node.id: node for node in workflow.nodes or []}
        middleware_defs: Dict[str, Any] = {}
        for node in workflow.nodes or []:
            mw_ids, mw_entries = _extract_middleware_entries(getattr(node, "middlewares", []) or [])
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

    def _apply_edge_bindings(self, record: RunRecord, node: NodeState) -> None:
        if not record.edge_bindings:
            return
        self._apply_edge_bindings_for_graph(
            node,
            record.edge_bindings,
            record.nodes,
        )

    def _apply_middleware_output_bindings(
        self,
        host_state: NodeState,
        middleware_state: NodeState,
    ) -> None:
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

    def _apply_frame_edge_bindings(self, frame: FrameRuntimeState, node: NodeState) -> None:
        if not frame.edge_bindings:
            return
        self._apply_edge_bindings_for_graph(
            node,
            frame.edge_bindings,
            frame.nodes,
        )

    def _apply_edge_bindings_for_graph(
        self,
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


run_registry = RunRegistry()
def _extract_middleware_entries(raw: Optional[Any]) -> Tuple[List[str], List[Dict[str, Any]]]:
    ids: List[str] = []
    defs: List[Dict[str, Any]] = []
    if not raw:
        return ids, defs
    if not isinstance(raw, list):
        return ids, defs
    for entry in raw:
        if entry is None:
            continue
        if isinstance(entry, dict):
            mw_id = entry.get("id") or entry.get("node_id") or entry.get("nodeId")
            if isinstance(mw_id, (UUID, str)) and mw_id:
                ids.append(str(mw_id))
            defs.append(entry)
            continue
        # Pydantic models / objects with id attributes
        candidate_id = getattr(entry, "id", None) or getattr(entry, "node_id", None) or getattr(entry, "nodeId", None)
        if candidate_id:
            mw_id = str(candidate_id)
            ids.append(mw_id)
            if hasattr(entry, "model_dump"):
                try:
                    defs.append(entry.model_dump(by_alias=True, exclude_none=True))
                except Exception:
                    defs.append({"id": mw_id})
            else:
                defs.append({"id": mw_id})
            continue
        mw_id = str(entry)
        if mw_id:
            ids.append(mw_id)
            defs.append({"id": mw_id})
    return ids, defs
