"""In-memory run tracking for the scheduler control plane."""

from __future__ import annotations

import asyncio
import copy
import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

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
from shared.models.ws import result as ws_result
from shared.models.ws.error import ErrorPayload


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _compute_definition_hash(workflow: StartRunRequestWorkflow) -> str:
    payload = workflow.to_dict()
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
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


FINAL_STATUSES = {"succeeded", "failed", "cancelled"}


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

    def to_summary(self) -> ListRuns200ResponseItemsInner:
        artifacts = [
            ListRuns200ResponseItemsInnerArtifactsInner.from_dict(self._format_artifact(artifact))
            for artifact in self.artifacts
        ] if self.artifacts else None
        nodes = [
            ListRuns200ResponseItemsInnerNodesInner.from_dict(self._format_node(node))
            for node in sorted(self.nodes.values(), key=lambda n: n.node_id)
        ] if self.nodes else None
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
        if task_id:
            node.task_id = task_id
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

    def _format_node(self, node: NodeState) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "nodeId": node.node_id,
            "taskId": node.task_id,
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
        if node.metadata is not None:
            payload["metadata"] = node.metadata
        if node.error:
            payload["error"] = node.error.to_dict()
        return payload


class RunRegistry:
    """Thread-safe run registry to coordinate REST and WebSocket layers."""

    def __init__(self) -> None:
        self._runs: Dict[str, RunRecord] = {}
        self._lock = asyncio.Lock()

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
            self._runs[run_id] = record
            return copy.deepcopy(record)

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
            record.status = "running"
            record.started_at = record.started_at or _utc_now()
            record.worker_id = worker_id
            record.task_id = task_id
            record.node_id = node_id
            record.node_type = node_type
            record.package_name = package_name
            record.package_version = package_version
            record.next_seq = max(record.next_seq, seq_used + 1)
            node_state = record.get_node(node_id, task_id=task_id)
            node_state.status = "running"
            node_state.worker_id = worker_id
            node_state.started_at = _utc_now()
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
            return copy.deepcopy(record)

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
            node_state = record.nodes.get(node_id)
            if not node_state or node_state.dispatch_id != dispatch_id:
                return copy.deepcopy(record)
            node_state.pending_ack = False
            node_state.ack_deadline = None
            record.refresh_rollup()
            return copy.deepcopy(record)

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
            node_state = record.nodes.get(node_id)
            if not node_state or node_state.dispatch_id != dispatch_id:
                return copy.deepcopy(record)
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
            return copy.deepcopy(record)

    async def record_result(
        self,
        run_id: str,
        payload: ws_result.ResultPayload,
    ) -> tuple[Optional[RunRecord], List[DispatchRequest]]:
        async with self._lock:
            record = self._runs.get(run_id)
            if not record:
                return None, []
            status = _normalise_status(payload.status.value)
            node_state = record.find_node_by_task(payload.task_id) or record.get_node(payload.task_id, task_id=payload.task_id)
            node_state.status = status
            node_state.finished_at = _utc_now()
            node_state.result = payload.result
            node_state.metadata = payload.metadata
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
            for dependent_id in node_state.dependents:
                dependent = record.nodes.get(dependent_id)
                if not dependent or dependent.status != "queued":
                    continue
                if dependent.pending_dependencies > 0:
                    dependent.pending_dependencies -= 1
                if dependent.pending_dependencies == 0 and not dependent.enqueued:
                    ready.append(self._build_dispatch_request(record, dependent))

            record.refresh_rollup()
            return copy.deepcopy(record), ready

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
            details = payload.context.details if payload.context and payload.context.details else None
            error = ListRuns200ResponseItemsInnerError(
                code=payload.code,
                message=payload.message,
                details=details,
            )
            record.error = error
            record.status = "failed"
            node_state = None
            if task_id:
                node_state = record.find_node_by_task(task_id)
            if not node_state and record.node_id:
                node_state = record.nodes.get(record.node_id)
            if node_state:
                node_state.status = "failed"
                node_state.finished_at = _utc_now()
                node_state.error = error
                node_state.enqueued = False
            record.refresh_rollup()
            return copy.deepcopy(record), []

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

    def _initialise_nodes(self, record: RunRecord) -> None:
        nodes: Dict[str, NodeState] = {}
        for node in record.workflow.nodes or []:
            package = getattr(node, "package", None)
            package_name = package.name if package else ""
            package_version = package.version if package else ""
            parameters = copy.deepcopy(getattr(node, "parameters", {}) or {})
            node_state = NodeState(
                node_id=node.id,
                task_id=node.id,
                node_type=node.type,
                package_name=package_name,
                package_version=package_version,
                parameters=parameters,
                concurrency_key=f"{record.run_id}:{node.id}",
            )
            nodes[node.id] = node_state

        for edge in record.workflow.edges or []:
            source = getattr(edge.source, "node", None)
            target = getattr(edge.target, "node", None)
            if not source or not target:
                continue
            if target not in nodes or source not in nodes:
                continue
            target_state = nodes[target]
            source_state = nodes[source]
            target_state.dependencies.append(source)
            target_state.pending_dependencies += 1
            source_state.dependents.append(target)

        record.nodes = nodes

    def _collect_ready_for_record(self, record: RunRecord) -> List[DispatchRequest]:
        ready: List[DispatchRequest] = []
        for node in record.nodes.values():
            if node.status == "queued" and node.pending_dependencies == 0 and not node.enqueued:
                ready.append(self._build_dispatch_request(record, node))
        return ready

    def _build_dispatch_request(self, record: RunRecord, node: NodeState) -> DispatchRequest:
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
            concurrency_key=node.concurrency_key,
            seq=seq,
            preferred_worker_id=preferred_worker_id,
        )


run_registry = RunRegistry()
