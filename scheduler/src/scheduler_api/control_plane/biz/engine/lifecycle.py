"""Run lifecycle mutations for the scheduler control plane."""

from __future__ import annotations

import copy
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

from ..domain.models import FrameRuntimeState, NodeState, RunRecord
from .pending import PendingNextRequests


@dataclass
class DispatchOutcome:
    record_snapshot: RunRecord
    node_snapshot: NodeState
    previous_status: str
    new_status: str


@dataclass
class AckOutcome:
    record_snapshot: RunRecord
    node_snapshot: NodeState
    previous_status: str


@dataclass
class CancelOutcome:
    record_snapshot: RunRecord
    cancelled_next: List[Tuple[str, str, str, Optional[str], Optional[str]]]


@dataclass
class ResetOutcome:
    record_snapshot: RunRecord
    node_snapshot: NodeState
    previous_status: str
    new_status: str


def mark_dispatched(
    record: RunRecord,
    *,
    worker_name: str,
    task_id: str,
    node_id: str,
    node_type: str,
    package_name: str,
    package_version: str,
    seq_used: int,
    resolve_node_state: Callable[..., Tuple[Optional[NodeState], Optional[FrameRuntimeState]]],
    pending_next_requests: PendingNextRequests,
    utc_now: Callable[[], datetime],
    final_statuses: set[str],
    resource_refs: Optional[List[Dict[str, Any]]] = None,
    affinity: Optional[Dict[str, Any]] = None,
    dispatch_id: Optional[str] = None,
    ack_deadline: Optional[datetime] = None,
) -> DispatchOutcome:
    previous_status = record.status
    timestamp = utc_now()
    record.status = "running"
    record.started_at = record.started_at or timestamp
    record.worker_name = worker_name
    record.task_id = task_id
    record.node_id = node_id
    record.node_type = node_type
    record.package_name = package_name
    record.package_version = package_version
    record.next_seq = max(record.next_seq, seq_used + 1)
    node_state, _frame_state = resolve_node_state(
        record,
        node_id=node_id,
        task_id=task_id,
    )
    if not node_state:
        node_state = record.get_node(node_id, task_id=task_id)
    node_state.status = "running"
    node_state.worker_name = worker_name
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
    if new_status in final_statuses:
        filtered: PendingNextRequests = {}
        for req_id, (
            run_id,
            worker_instance_id,
            worker_name,
            deadline,
            pending_node_id,
            middleware_id,
            target_task_id,
        ) in pending_next_requests.items():
            if run_id == record.run_id:
                continue
            filtered[req_id] = (
                run_id,
                worker_instance_id,
                worker_name,
                deadline,
                pending_node_id,
                middleware_id,
                target_task_id,
            )
        pending_next_requests.clear()
        pending_next_requests.update(filtered)
    record_snapshot = copy.deepcopy(record)
    node_snapshot = copy.deepcopy(node_state)
    return DispatchOutcome(
        record_snapshot=record_snapshot,
        node_snapshot=node_snapshot,
        previous_status=previous_status,
        new_status=new_status,
    )


def mark_acknowledged(
    record: RunRecord,
    *,
    node_id: str,
    dispatch_id: str,
    find_node_by_dispatch: Callable[..., Tuple[Optional[NodeState], Optional[FrameRuntimeState]]],
) -> Optional[AckOutcome]:
    node_state, _frame_state = find_node_by_dispatch(record, dispatch_id)
    if not node_state or node_state.node_id != node_id:
        return None
    previous_status = record.status
    node_state.pending_ack = False
    node_state.ack_deadline = None
    record.refresh_rollup()
    record_snapshot = copy.deepcopy(record)
    node_snapshot = copy.deepcopy(node_state)
    return AckOutcome(
        record_snapshot=record_snapshot,
        node_snapshot=node_snapshot,
        previous_status=previous_status,
    )


def cancel_run(
    record: RunRecord,
    *,
    run_id: str,
    pending_next_requests: PendingNextRequests,
    utc_now: Callable[[], datetime],
    final_statuses: set[str],
) -> CancelOutcome:
    def _cancel_nodes(nodes: Dict[str, NodeState], timestamp: datetime) -> None:
        for node in nodes.values():
            if node.status in final_statuses:
                continue
            node.status = "cancelled"
            node.enqueued = False
            node.pending_dependencies = 0
            node.pending_ack = False
            node.dispatch_id = None
            node.ack_deadline = None
            node.finished_at = timestamp

    timestamp = utc_now()
    _cancel_nodes(record.nodes, timestamp)
    for frame in record.active_frames.values():
        _cancel_nodes(frame.nodes, timestamp)
    record.active_frames.clear()
    record.frame_stack.clear()
    record.status = "cancelled"
    record.finished_at = timestamp
    cancelled_next: List[Tuple[str, str, str, Optional[str], Optional[str]]] = []
    remaining_next: PendingNextRequests = {}
    for req_id, (
        req_run_id,
        worker_instance_id,
        worker_name,
        deadline,
        node_id,
        middleware_id,
        target_task_id,
    ) in pending_next_requests.items():
        if req_run_id == run_id:
            if worker_instance_id or worker_name:
                cancelled_next.append(
                    (
                        req_id,
                        worker_instance_id or worker_name or "",
                        req_run_id,
                        node_id,
                        middleware_id,
                    )
                )
            continue
        remaining_next[req_id] = (
            req_run_id,
            worker_instance_id,
            worker_name,
            deadline,
            node_id,
            middleware_id,
            target_task_id,
        )
    pending_next_requests.clear()
    pending_next_requests.update(remaining_next)
    record.refresh_rollup()
    record.status = "cancelled"
    record_snapshot = copy.deepcopy(record)
    return CancelOutcome(
        record_snapshot=record_snapshot,
        cancelled_next=cancelled_next,
    )


def reset_after_ack_timeout(
    record: RunRecord,
    *,
    node_id: str,
    dispatch_id: str,
    find_node_by_dispatch: Callable[..., Tuple[Optional[NodeState], Optional[FrameRuntimeState]]],
) -> Optional[ResetOutcome]:
    node_state, _frame_state = find_node_by_dispatch(record, dispatch_id)
    if not node_state or node_state.node_id != node_id:
        return None
    previous_status = record.status
    previous_worker = node_state.worker_name
    previous_node_type = node_state.node_type
    previous_package_name = node_state.package_name
    previous_package_version = node_state.package_version
    previous_task_id = node_state.task_id

    node_state.status = "queued"
    node_state.worker_name = None
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
    if record.worker_name == previous_worker:
        record.worker_name = None
    if record.package_name == previous_package_name:
        record.package_name = None
    if record.package_version == previous_package_version:
        record.package_version = None
    record.refresh_rollup()
    new_status = record.status
    record_snapshot = copy.deepcopy(record)
    node_snapshot = copy.deepcopy(node_state)
    return ResetOutcome(
        record_snapshot=record_snapshot,
        node_snapshot=node_snapshot,
        previous_status=previous_status,
        new_status=new_status,
    )


def reset_after_worker_cancel(
    record: RunRecord,
    node_state: NodeState,
    *,
    pending_next_requests: PendingNextRequests,
) -> ResetOutcome:
    previous_status = record.status
    node_state.status = "queued"
    node_state.worker_name = None
    node_state.started_at = None
    node_state.finished_at = None
    node_state.seq = None
    node_state.pending_ack = False
    node_state.dispatch_id = None
    node_state.ack_deadline = None
    node_state.enqueued = False
    node_state.error = None
    # Ensure the node can be re-dispatched immediately.
    node_state.pending_dependencies = 0
    node_state.chain_blocked = False
    # Drop any pending middleware.next waiting on this task.
    remaining_next: PendingNextRequests = {}
    for req_id, (
        run_id,
        worker_instance_id,
        worker_name,
        deadline,
        pending_node_id,
        middleware_id,
        target_task_id,
    ) in pending_next_requests.items():
        if run_id == record.run_id and target_task_id == node_state.task_id:
            continue
        remaining_next[req_id] = (
            run_id,
            worker_instance_id,
            worker_name,
            deadline,
            pending_node_id,
            middleware_id,
            target_task_id,
        )
    pending_next_requests.clear()
    pending_next_requests.update(remaining_next)

    record.refresh_rollup()
    new_status = record.status
    record_snapshot = copy.deepcopy(record)
    node_snapshot = copy.deepcopy(node_state)
    return ResetOutcome(
        record_snapshot=record_snapshot,
        node_snapshot=node_snapshot,
        previous_status=previous_status,
        new_status=new_status,
    )
