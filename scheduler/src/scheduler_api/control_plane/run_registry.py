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

LOGGER = logging.getLogger(__name__)


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
        state_payload = self._build_node_state_payload(
            node,
            last_updated_at=node.finished_at or node.started_at,
        )
        if state_payload:
            payload["state"] = state_payload
        return payload


class RunRegistry:
    """Thread-safe run registry to coordinate REST and WebSocket layers."""

    def __init__(self) -> None:
        self._runs: Dict[str, RunRecord] = {}
        self._lock = asyncio.Lock()

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
            node_state = record.get_node(node_id, task_id=task_id)
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
            record_snapshot = copy.deepcopy(record)
            node_snapshot = copy.deepcopy(node_state)
        tasks = [self._publish_node_state(record_snapshot, node_snapshot)]
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
            node_state = record.nodes.get(node_id)
            if not node_state or node_state.dispatch_id != dispatch_id:
                return copy.deepcopy(record)
            previous_status = record.status
            node_state.pending_ack = False
            node_state.ack_deadline = None
            record.refresh_rollup()
            record_snapshot = copy.deepcopy(record)
            node_snapshot = copy.deepcopy(node_state)
        tasks = [self._publish_node_state(record_snapshot, node_snapshot)]
        if record_snapshot.status != previous_status:
            tasks.append(self._publish_run_state(record_snapshot))
        tasks.append(self._publish_run_snapshot(record_snapshot))
        await asyncio.gather(*tasks)
        return record_snapshot

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
        tasks = [self._publish_node_state(record_snapshot, node_snapshot)]
        if new_status != previous_status:
            tasks.append(self._publish_run_state(record_snapshot))
        tasks.append(self._publish_run_snapshot(record_snapshot))
        await asyncio.gather(*tasks)
        return record_snapshot

    async def record_result(
        self,
        run_id: str,
        payload: ws_result.ResultPayload,
    ) -> tuple[Optional[RunRecord], List[DispatchRequest]]:
        async with self._lock:
            record = self._runs.get(run_id)
            if not record:
                return None, []
            previous_status = record.status
            status = _normalise_status(payload.status.value)
            node_state = record.find_node_by_task(payload.task_id) or record.get_node(payload.task_id, task_id=payload.task_id)
            timestamp = _utc_now()
            node_state.status = status
            node_state.finished_at = timestamp
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
        if new_status != previous_status:
            tasks.append(self._publish_run_state(record_snapshot))
        tasks.append(self._publish_run_snapshot(record_snapshot))
        await asyncio.gather(*tasks)
        return record_snapshot, ready

    async def record_feedback(
        self,
        payload: FeedbackPayload,
    ) -> None:
        async with self._lock:
            record = self._runs.get(payload.run_id)
            if not record:
                return
            node_state = (
                record.find_node_by_task(payload.task_id)
                or record.nodes.get(payload.task_id)
                or record.get_node(payload.task_id, task_id=payload.task_id)
            )
            metadata = node_state.metadata or {}
            node_state.metadata = metadata
            changed_state = False
            now = _utc_now()
            metadata["lastUpdatedAt"] = now.isoformat()
            if payload.stage:
                metadata["stage"] = payload.stage
                changed_state = True
            if payload.progress is not None:
                metadata["progress"] = payload.progress
                changed_state = True
            if payload.message:
                metadata["message"] = payload.message
                changed_state = True
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
            publish_node_state = changed_state and record_snapshot and node_snapshot
        tasks: List[asyncio.Future[Any]] = []
        if publish_node_state:
            tasks.append(self._publish_node_state(record_snapshot, node_snapshot))
        if chunk_events and record_snapshot:
            node_for_delta = node_snapshot or record_snapshot.nodes.get(node_state.node_id)
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
        if tasks:
            await asyncio.gather(*tasks)

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
            previous_status = record.status
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
            node_snapshot = None
            if node_state:
                node_state.status = "failed"
                node_state.finished_at = _utc_now()
                node_state.error = error
                node_state.enqueued = False
                node_snapshot = copy.deepcopy(node_state)
            record.refresh_rollup()
            record_snapshot = copy.deepcopy(record)
        tasks = []
        if node_snapshot is not None:
            tasks.append(self._publish_node_state(record_snapshot, node_snapshot))
        if record_snapshot.status != previous_status:
            tasks.append(self._publish_run_state(record_snapshot))
        tasks.append(self._publish_run_snapshot(record_snapshot))
        if tasks:
            await asyncio.gather(*tasks)
        return record_snapshot, []

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
