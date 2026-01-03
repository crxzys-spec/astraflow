"""Data models for the scheduler run registry."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

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
from scheduler_api.models.start_run_request_workflow import StartRunRequestWorkflow
from scheduler_api.engine.events.format import format_artifact, format_node


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


FINAL_STATUSES = {"succeeded", "failed", "cancelled", "skipped"}


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
    constraints: Dict[str, Any] = field(default_factory=dict)
    preferred_worker_name: Optional[str] = None
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
    worker_name: Optional[str] = None
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
    owner_id: Optional[str] = None
    created_at: datetime = field(default_factory=_utc_now)
    status: str = "queued"
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    worker_name: Optional[str] = None
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
            ListRuns200ResponseItemsInnerArtifactsInner.from_dict(
                format_artifact(
                    artifact,
                    default_worker_name=self.worker_name,
                )
            )
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
            ListRuns200ResponseItemsInnerNodesInner.from_dict(
                format_node(node, record=self)
            )
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
