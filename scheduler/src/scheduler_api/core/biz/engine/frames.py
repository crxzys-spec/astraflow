"""Frame and dependency release helpers for the scheduler control plane."""

from __future__ import annotations

import copy
from datetime import datetime
from typing import Callable, Dict, List, Optional, Set, Tuple

from shared.models.biz.exec.next.response import ExecMiddlewareNextResponse

from ..domain.models import DispatchRequest, FrameRuntimeState, NodeState, RunRecord
from .pending import PendingNextRequests


def release_dependents(
    record: RunRecord,
    node_state: NodeState,
    frame_state: Optional[FrameRuntimeState],
    ready: List[DispatchRequest],
    *,
    is_container_node: Callable[[NodeState], bool],
    is_host_with_middleware: Callable[[NodeState], bool],
    should_auto_dispatch: Callable[[NodeState], bool],
    start_container_execution: Callable[..., List[DispatchRequest]],
    build_dispatch_request_for_node: Callable[[RunRecord, NodeState], DispatchRequest],
    state_events: Optional[List[Tuple[RunRecord, NodeState]]] = None,
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
        if is_container_node(dependent):
            if dependent.pending_dependencies > 0 or dependent.enqueued:
                continue
            parent_frame_id = frame_state.frame_id if frame_state else None
            frame_ready = start_container_execution(
                record,
                dependent,
                parent_frame_id=parent_frame_id,
                state_events=state_events,
            )
            ready.extend(frame_ready)
            continue
        if is_host_with_middleware(dependent):
            if dependent.pending_dependencies == 0 and not dependent.enqueued:
                ready.append(build_dispatch_request_for_node(record, dependent))
            continue
        if should_auto_dispatch(dependent):
            ready.append(build_dispatch_request_for_node(record, dependent))


def complete_frame_if_needed(
    record: RunRecord,
    frame: FrameRuntimeState,
    *,
    pending_next_requests: PendingNextRequests,
    is_host_with_middleware: Callable[[NodeState], bool],
    get_parent_graph: Callable[[RunRecord, Optional[str]], Tuple[Dict[str, NodeState], Optional[FrameRuntimeState]]],
    pop_frame: Callable[[RunRecord, str], None],
    build_dispatch_request_for_node: Callable[[RunRecord, NodeState], DispatchRequest],
    utc_now: Callable[[], datetime],
    final_statuses: Set[str],
) -> Tuple[List[DispatchRequest], Optional[NodeState], List[Tuple[Optional[str], ExecMiddlewareNextResponse]]]:
    nodes = list(frame.nodes.values())
    failed = any(node.status == "failed" for node in nodes)
    terminal = all(node.status in final_statuses for node in nodes)
    if not failed and not terminal:
        return [], None, []

    if failed:
        for node in nodes:
            if node.status not in final_statuses:
                node.status = "cancelled"
                node.enqueued = False

    parent_nodes, _ = get_parent_graph(record, frame.parent_frame_id)
    container_node = parent_nodes.get(frame.container_node_id)
    if not container_node:
        pop_frame(record, frame.frame_id)
        return [], None, []

    now = utc_now()
    container_node.finished_at = now
    container_node.enqueued = False
    container_node.pending_ack = False
    container_node.dispatch_id = None
    container_node.ack_deadline = None
    container_node.worker_name = None
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
        if is_host_with_middleware(container_node):
            # Container host still has middleware chain to complete; keep it queued/blocked until middleware finalises.
            container_node.status = "queued"
            container_node.finished_at = None
            container_node.chain_blocked = True
            container_node.pending_dependencies = 0
        else:
            container_node.status = "succeeded"

    if container_node.result is None or not isinstance(container_node.result, dict):
        container_node.result = {}

    record.completed_frames[frame.frame_id] = {
        node_id: copy.deepcopy(node_state) for node_id, node_state in frame.nodes.items()
    }
    pop_frame(record, frame.frame_id)
    ready: List[DispatchRequest] = []
    next_responses: List[Tuple[Optional[str], ExecMiddlewareNextResponse]] = []
    pending_next_to_clear = [
        (req_id, worker_instance_id, run_id, node_id, middleware_id)
        for req_id, (
            run_id,
            worker_instance_id,
            worker_name,
            deadline,
            node_id,
            middleware_id,
            target_task_id,
        ) in pending_next_requests.items()
        if target_task_id == container_node.task_id and run_id == record.run_id
    ]
    for req_id, worker_instance_id, run_id, node_id, middleware_id in pending_next_to_clear:
        pending_next_requests.pop(req_id, None)
        err_body = None
        if container_node.error:
            err_body = {"code": container_node.error.code, "message": container_node.error.message}
        elif failed:
            err_body = {"code": "next_failed", "message": f"target {container_node.node_id} status failed"}
        resp = ExecMiddlewareNextResponse(
            requestId=req_id,
            runId=run_id,
            nodeId=node_id or "",
            middlewareId=middleware_id or "",
            result=container_node.result,
            error=err_body,
        )
        next_responses.append((worker_instance_id, resp))
    # When the container has middlewares, the execution unit isn't finished yet; let the outermost middleware finalise and release dependents.
    if is_host_with_middleware(container_node):
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
            ready.append(build_dispatch_request_for_node(record, dependent))
    return ready, container_node, next_responses
