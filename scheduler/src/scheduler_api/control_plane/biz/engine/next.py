"""Helpers for middleware.next request handling."""

from __future__ import annotations

import copy
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Callable, Dict, Iterable, List, Optional, Set, Tuple

from shared.models.biz.exec.next.request import ExecMiddlewareNextRequest

from ..domain.models import DispatchRequest, FrameRuntimeState, NodeState, RunRecord

PendingNextRequests = Dict[
    str,
    Tuple[
        str,
        Optional[str],
        Optional[str],
        Optional[datetime],
        Optional[str],
        Optional[str],
        Optional[str],
    ],
]


@dataclass
class NextRequestOutcome:
    ready: List[DispatchRequest]
    error_code: Optional[str]
    state_events: List[Tuple[RunRecord, NodeState]]
    record_snapshot: Optional[RunRecord]
    node_snapshot: Optional[NodeState]


def _iter_all_nodes(record: RunRecord) -> Iterable[NodeState]:
    for node in record.nodes.values():
        yield node
    for frame in record.active_frames.values():
        for node in frame.nodes.values():
            yield node


def _find_chain_for_middleware(
    record: RunRecord,
    middleware_id: Optional[str],
) -> Tuple[Optional[str], Optional[List[str]]]:
    if not middleware_id:
        return None, None
    for node in _iter_all_nodes(record):
        chain_ids = getattr(node, "middlewares", []) or []
        if middleware_id in chain_ids:
            return node.node_id, list(chain_ids)
    return None, None


def handle_next_request(
    *,
    record: RunRecord,
    payload: ExecMiddlewareNextRequest,
    worker_name: Optional[str],
    worker_instance_id: Optional[str],
    pending_next_requests: PendingNextRequests,
    resolve_node_state: Callable[..., Tuple[Optional[NodeState], Optional[FrameRuntimeState]]],
    is_container_node: Callable[[NodeState], bool],
    is_middleware_node: Callable[[NodeState], bool],
    is_host_with_middleware: Callable[[NodeState], bool],
    start_container_execution: Callable[..., List[DispatchRequest]],
    build_dispatch_request: Callable[..., DispatchRequest],
    utc_now: Callable[[], datetime],
    final_statuses: Set[str],
) -> NextRequestOutcome:
    state_events: List[Tuple[RunRecord, NodeState]] = []
    record_snapshot: Optional[RunRecord] = None
    node_snapshot: Optional[NodeState] = None
    ready: List[DispatchRequest] = []

    if payload.requestId in pending_next_requests:
        return NextRequestOutcome([], "next_duplicate", [], None, None)

    host_node_id, chain = _find_chain_for_middleware(record, payload.middlewareId)
    if not chain:
        return NextRequestOutcome([], "next_no_chain", [], None, None)

    try:
        current_index = payload.chainIndex if payload.chainIndex is not None else chain.index(payload.middlewareId)
    except ValueError:
        return NextRequestOutcome([], "next_invalid_chain", [], None, None)

    target_index = current_index + 1
    if target_index < len(chain):
        target_node_id = chain[target_index]
        target_chain_index = target_index
    else:
        target_node_id = host_node_id
        target_chain_index = None

    node_state, frame_state = resolve_node_state(
        record,
        node_id=target_node_id,
        task_id=None,
    )
    if not node_state:
        return NextRequestOutcome([], "next_target_not_ready", [], None, None)

    # Prevent re-entering a container while its frame is still active (e.g., repeated middleware.next).
    if is_container_node(node_state):
        parent_frame_id = frame_state.frame_id if frame_state else None
        active_for_container = next(
            (
                frame
                for frame in record.active_frames.values()
                if frame.definition.container_node_id == node_state.node_id
                and frame.definition.parent_frame_id == parent_frame_id
                and frame.status not in final_statuses
            ),
            None,
        )
        if active_for_container:
            return NextRequestOutcome([], "next_target_not_ready", [], None, None)

    is_chain_node = is_middleware_node(node_state) or is_host_with_middleware(node_state)
    if is_chain_node:
        # Allow middleware/host targets to be re-queued after a terminal status or stale running state.
        if node_state.enqueued or node_state.pending_dependencies != 0:
            return NextRequestOutcome([], "next_target_not_ready", [], None, None)
        if node_state.status in final_statuses or node_state.status == "running":
            node_state.status = "queued"
            node_state.worker_name = None
            node_state.pending_ack = False
            node_state.dispatch_id = None
            node_state.ack_deadline = None
            node_state.enqueued = False
            node_state.finished_at = None
            state_events.append((copy.deepcopy(record), copy.deepcopy(node_state)))
        node_state.chain_blocked = False

    node_state.enqueued = False

    parent_frame_id = frame_state.frame_id if frame_state else None
    if is_container_node(node_state):
        frame_ready = start_container_execution(
            record,
            node_state,
            parent_frame_id=parent_frame_id,
            state_events=state_events,
        )
        deadline = None
        if payload.timeoutMs and payload.timeoutMs > 0:
            deadline = utc_now() + timedelta(milliseconds=payload.timeoutMs)
        pending_next_requests[payload.requestId] = (
            record.run_id,
            worker_instance_id,
            worker_name,
            deadline,
            payload.nodeId,
            payload.middlewareId,
            node_state.task_id,
        )
        ready.extend(frame_ready)
        return NextRequestOutcome(ready, None, state_events, None, None)

    dispatch = build_dispatch_request(
        record,
        node_state,
        host_node_id=host_node_id,
        middleware_chain=chain,
        chain_index=target_chain_index,
    )
    deadline = None
    if payload.timeoutMs and payload.timeoutMs > 0:
        deadline = utc_now() + timedelta(milliseconds=payload.timeoutMs)
    pending_next_requests[payload.requestId] = (
        record.run_id,
        worker_instance_id,
        worker_name,
        deadline,
        payload.nodeId,
        payload.middlewareId,
        node_state.task_id,
    )
    record_snapshot = copy.deepcopy(record)
    node_snapshot = copy.deepcopy(node_state)
    ready.append(dispatch)
    return NextRequestOutcome(ready, None, state_events, record_snapshot, node_snapshot)
