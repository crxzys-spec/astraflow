"""Update helpers for run registry feedback, results, and command errors."""

from __future__ import annotations

import copy
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from scheduler_api.models.list_runs200_response_items_inner_error import (
    ListRuns200ResponseItemsInnerError,
)
from shared.models.biz.exec.error import ExecErrorPayload
from shared.models.biz.exec.feedback import ExecFeedbackPayload

from ..domain.models import DispatchRequest, FrameRuntimeState, NodeState, RunRecord
from shared.models.biz.exec.next.response import ExecMiddlewareNextResponse
from shared.models.biz.exec.result import ExecResultPayload


@dataclass
class FeedbackOutcome:
    record_snapshot: Optional[RunRecord]
    node_snapshot: Optional[NodeState]
    node_state: NodeState
    publish_node_state: bool
    chunk_events: List[Dict[str, Any]]
    result_deltas: List[Dict[str, Any]]


@dataclass
class CommandErrorOutcome:
    record_snapshot: RunRecord
    node_snapshot: Optional[NodeState]
    container_snapshot: Optional[NodeState]
    ready: List[DispatchRequest]
    previous_status: str


@dataclass
class RecordResultOutcome:
    record_snapshot: RunRecord
    node_snapshot: NodeState
    host_snapshot: Optional[NodeState]
    container_snapshot: Optional[NodeState]
    ready: List[DispatchRequest]
    next_responses: List[Tuple[Optional[str], ExecMiddlewareNextResponse]]
    state_events: List[Tuple[RunRecord, NodeState]]
    previous_status: str
    new_status: str
    node_state: NodeState
    status: str


def apply_feedback(
    record: RunRecord,
    payload: ExecFeedbackPayload,
    *,
    resolve_node_state: Callable[..., Tuple[Optional[NodeState], Optional[FrameRuntimeState]]],
    merge_result_updates: Callable[[Dict[str, Any], Dict[str, Any]], List[Dict[str, Any]]],
    utc_now: Callable[[], datetime],
) -> FeedbackOutcome:
    node_state, _frame_state = resolve_node_state(
        record,
        node_id=None,
        task_id=payload.task_id,
    )
    if not node_state:
        node_state = record.get_node(payload.task_id, task_id=payload.task_id)
    metadata = node_state.metadata or {}
    node_state.metadata = metadata
    changed_state = False
    now = utc_now()
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
        result_changes = merge_result_updates(node_state.result, incoming_results)
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
    return FeedbackOutcome(
        record_snapshot=record_snapshot,
        node_snapshot=node_snapshot,
        node_state=node_state,
        publish_node_state=publish_node_state,
        chunk_events=chunk_events,
        result_deltas=result_deltas,
    )


def apply_command_error(
    record: RunRecord,
    payload: ExecErrorPayload,
    *,
    task_id: Optional[str],
    resolve_node_state: Callable[..., Tuple[Optional[NodeState], Optional[FrameRuntimeState]]],
    complete_frame_if_needed: Callable[..., Tuple[List[DispatchRequest], Optional[NodeState], List[Any]]],
    utc_now: Callable[[], datetime],
) -> CommandErrorOutcome:
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
        node_state, frame_state = resolve_node_state(
            record,
            node_id=None,
            task_id=task_id,
        )
    if not node_state and record.node_id:
        node_state, frame_state = resolve_node_state(
            record,
            node_id=record.node_id,
            task_id=None,
        )
    node_snapshot = None
    container_snapshot = None
    ready: List[DispatchRequest] = []
    if node_state:
        node_state.status = "failed"
        node_state.finished_at = utc_now()
        node_state.error = error
        node_state.enqueued = False
        node_state.pending_ack = False
        node_state.dispatch_id = None
        node_state.ack_deadline = None
        node_state.worker_name = None
        if frame_state:
            frame_ready, container_node, _ = complete_frame_if_needed(record, frame_state)
            ready.extend(frame_ready)
            if container_node and frame_state.parent_frame_id is None:
                container_snapshot = copy.deepcopy(container_node)
        node_snapshot = copy.deepcopy(node_state)
    record.refresh_rollup()
    record_snapshot = copy.deepcopy(record)
    return CommandErrorOutcome(
        record_snapshot=record_snapshot,
        node_snapshot=node_snapshot,
        container_snapshot=container_snapshot,
        ready=ready,
        previous_status=previous_status,
    )


def apply_record_result(
    record: RunRecord,
    payload: ExecResultPayload,
    *,
    resolve_node_state: Callable[..., Tuple[Optional[NodeState], Optional[FrameRuntimeState]]],
    is_host_with_middleware: Callable[[NodeState], bool],
    is_middleware_node: Callable[[NodeState], bool],
    apply_edge_bindings: Callable[..., None],
    apply_frame_edge_bindings: Callable[..., None],
    apply_middleware_output_bindings: Callable[..., None],
    release_dependents: Callable[..., None],
    complete_frame_if_needed: Callable[..., Tuple[List[DispatchRequest], Optional[NodeState], List[Tuple[Optional[str], ExecMiddlewareNextResponse]]]],
    finalise_pending_next: Callable[..., List[Tuple[Optional[str], ExecMiddlewareNextResponse]]],
    utc_now: Callable[[], datetime],
    normalise_status: Callable[[str], str],
    final_statuses: Set[str],
) -> RecordResultOutcome:
    previous_status = record.status
    status = normalise_status(payload.status.value)
    node_state, frame_state = resolve_node_state(
        record,
        node_id=None,
        task_id=payload.task_id,
    )
    if not node_state:
        node_state = record.get_node(payload.task_id, task_id=payload.task_id)
        frame_state = None
    timestamp = utc_now()
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
    state_events: List[Tuple[RunRecord, NodeState]] = []
    next_responses: List[Tuple[Optional[str], ExecMiddlewareNextResponse]] = []
    # Host nodes with middleware chains keep looping; do not release dependents or finalize yet.
    if not is_host_with_middleware(node_state):
        if status in {"succeeded", "skipped"}:
            if frame_state:
                apply_frame_edge_bindings(frame_state, node_state)
            else:
                apply_edge_bindings(record, node_state)
            release_dependents(record, node_state, frame_state, ready, state_events)
    else:
        # Allow the host to be dispatched again by middleware.next()
        if status == "skipped":
            node_state.status = "skipped"
            node_state.enqueued = False
            node_state.pending_dependencies = 0
        else:
            node_state.status = "queued"
            node_state.enqueued = False
            node_state.pending_dependencies = 0
        node_state.chain_blocked = True

    # Middleware completion finalises the host and releases its dependents.
    host_snapshot: Optional[NodeState] = None
    if is_middleware_node(node_state):
        if status in {"succeeded", "skipped"}:
            # Mark middleware terminal so the rollup can complete; next() can re-queue it when needed.
            node_state.status = status
            node_state.enqueued = False
            node_state.pending_dependencies = 0
            node_state.chain_blocked = False
        else:
            node_state.chain_blocked = True

        host_id = node_state.metadata.get("host_node_id") if node_state.metadata else None
        if host_id:
            host_state, host_frame = resolve_node_state(record, node_id=str(host_id), task_id=None)
            if host_state:
                # Surface middleware outputs onto the host payload so downstream bindings can consume them.
                apply_middleware_output_bindings(host_state, node_state)
                chain_index = node_state.metadata.get("chain_index") if node_state.metadata else None
                # Finalise host when chain ends (outermost) or when skipping.
                is_outermost = chain_index is None or chain_index == 0
                should_finalise_host = status == "skipped" or is_outermost
                if should_finalise_host and host_state.status not in final_statuses:
                    host_state.status = status
                    host_state.finished_at = timestamp
                    # Keep host data isolated; middleware data remains on the middleware node
                    host_state.result = host_state.result
                    host_state.metadata = host_state.metadata
                    host_state.artifacts = host_state.artifacts
                    host_state.error = host_state.error
                    host_state.enqueued = False
                    host_state.pending_dependencies = 0
                    host_state.chain_blocked = False
                    if status in {"succeeded", "skipped"}:
                        if host_frame:
                            apply_frame_edge_bindings(host_frame, host_state)
                        else:
                            apply_edge_bindings(record, host_state)
                        release_dependents(record, host_state, host_frame, ready, state_events)
                host_snapshot = copy.deepcopy(host_state)

    container_snapshot: Optional[NodeState] = None
    if frame_state:
        frame_ready, container_node, frame_next_responses = complete_frame_if_needed(record, frame_state)
        ready.extend(frame_ready)
        next_responses.extend(frame_next_responses)
        if container_node and frame_state.parent_frame_id is None:
            container_snapshot = copy.deepcopy(container_node)

    # Resolve pending middleware.next responses targeting this task
    next_responses.extend(finalise_pending_next(payload, node_state, status=status))

    record.refresh_rollup()
    new_status = record.status
    record_snapshot = copy.deepcopy(record)
    node_snapshot = copy.deepcopy(node_state)
    return RecordResultOutcome(
        record_snapshot=record_snapshot,
        node_snapshot=node_snapshot,
        host_snapshot=host_snapshot,
        container_snapshot=container_snapshot,
        ready=ready,
        next_responses=next_responses,
        state_events=state_events,
        previous_status=previous_status,
        new_status=new_status,
        node_state=node_state,
        status=status,
    )
