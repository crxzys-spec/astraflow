"""Dispatch/ready helpers for the run registry."""

from __future__ import annotations

import copy
import logging
from datetime import datetime
from typing import Callable, Dict, List, Optional, Tuple

from ..domain.models import (
    DispatchRequest,
    FrameDefinition,
    FrameRuntimeState,
    NodeState,
    RunRecord,
)


def is_middleware_node(node: NodeState) -> bool:
    return bool(node.metadata and node.metadata.get("role") == "middleware")


def is_host_with_middleware(node: NodeState) -> bool:
    return bool(node.middlewares) and not is_middleware_node(node)


def is_container_node(node: NodeState) -> bool:
    if node.node_type == "workflow.container":
        return True
    return bool(node.metadata and node.metadata.get("role") == "container")


def is_container_ready(node: NodeState) -> bool:
    if not is_container_node(node):
        return False
    if node.middlewares:
        # Containers with middleware still follow the middleware chain rules.
        return False
    if getattr(node, "chain_blocked", False):
        return False
    return node.status == "queued" and node.pending_dependencies == 0 and not node.enqueued


def is_first_middleware(node: NodeState) -> bool:
    if not is_middleware_node(node):
        return False
    chain_index = node.metadata.get("chain_index") if node.metadata else None
    return chain_index is None or chain_index == 0


def should_auto_dispatch(node: NodeState) -> bool:
    if node.status != "queued" or node.pending_dependencies != 0 or node.enqueued:
        return False
    if getattr(node, "chain_blocked", False):
        return False
    if is_host_with_middleware(node):
        return False
    return True


def resolve_middleware_chain(
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


def build_dispatch_request_for_node(
    record: RunRecord,
    node: NodeState,
) -> DispatchRequest:
    host_node_id = None
    middleware_chain = None
    chain_index = None
    chain_info = resolve_middleware_chain(record, node)
    if chain_info:
        host_node_id, middleware_chain, chain_index = chain_info
    return build_dispatch_request(
        record,
        node,
        host_node_id=host_node_id,
        middleware_chain=middleware_chain,
        chain_index=chain_index,
    )


def collect_ready_for_record(
    record: RunRecord,
    *,
    is_container_node: Callable[[NodeState], bool],
    is_container_ready: Callable[[NodeState], bool],
    should_auto_dispatch: Callable[[NodeState], bool],
    start_container_execution: Callable[..., List[DispatchRequest]],
    build_dispatch_request_for_node: Callable[[RunRecord, NodeState], DispatchRequest],
    state_events: Optional[List[Tuple[RunRecord, NodeState]]] = None,
) -> List[DispatchRequest]:
    ready: List[DispatchRequest] = []
    for node in record.nodes.values():
        if is_container_node(node):
            if not is_container_ready(node):
                continue
            frame_ready = start_container_execution(
                record,
                node,
                parent_frame_id=None,
                state_events=state_events,
            )
            ready.extend(frame_ready)
            continue
        if not should_auto_dispatch(node):
            continue
        ready.append(build_dispatch_request_for_node(record, node))
    return ready


def collect_ready_for_frame(
    record: RunRecord,
    frame: FrameRuntimeState,
    *,
    is_container_node: Callable[[NodeState], bool],
    is_container_ready: Callable[[NodeState], bool],
    should_auto_dispatch: Callable[[NodeState], bool],
    start_container_execution: Callable[..., List[DispatchRequest]],
    build_dispatch_request_for_node: Callable[[RunRecord, NodeState], DispatchRequest],
    state_events: Optional[List[Tuple[RunRecord, NodeState]]] = None,
) -> List[DispatchRequest]:
    ready: List[DispatchRequest] = []
    for node in frame.nodes.values():
        if is_container_node(node):
            if not is_container_ready(node):
                continue
            frame_ready = start_container_execution(
                record,
                node,
                parent_frame_id=frame.frame_id,
                state_events=state_events,
            )
            ready.extend(frame_ready)
            continue
        if not should_auto_dispatch(node):
            continue
        ready.append(build_dispatch_request_for_node(record, node))
    return ready


def start_container_execution(
    record: RunRecord,
    container_node: NodeState,
    *,
    parent_frame_id: Optional[str],
    state_events: Optional[List[Tuple[RunRecord, NodeState]]] = None,
    find_frame_for_container: Callable[..., Optional[FrameDefinition]],
    build_container_frames: Callable[
        ...,
        Tuple[Dict[str, FrameDefinition], Dict[Tuple[Optional[str], str], FrameDefinition]],
    ],
    activate_frame: Callable[..., FrameRuntimeState],
    collect_ready_for_frame: Callable[..., List[DispatchRequest]],
    utc_now: Callable[[], datetime],
    logger: logging.Logger,
) -> List[DispatchRequest]:
    frame_definition = find_frame_for_container(
        record,
        container_node_id=container_node.node_id,
        parent_frame_id=parent_frame_id,
    )
    if not frame_definition:
        frames, frames_by_parent = build_container_frames(record.workflow)
        record.frames = frames
        record.frames_by_parent = frames_by_parent
        frame_definition = find_frame_for_container(
            record,
            container_node_id=container_node.node_id,
            parent_frame_id=parent_frame_id,
        )
    if not frame_definition:
        logger.error(
            "Container node %s missing subgraph frame (parent_frame=%s)",
            container_node.node_id,
            parent_frame_id,
        )
        container_node.status = "failed"
        container_node.enqueued = True
        container_node.finished_at = utc_now()
        return []

    if container_node.started_at is None:
        container_node.started_at = utc_now()
    container_node.status = "running"
    container_node.enqueued = True
    container_node.metadata = container_node.metadata or {}
    container_node.metadata["frameId"] = frame_definition.frame_id
    frame_state = activate_frame(record, frame_definition)
    if state_events is not None:
        # Emit a fresh state event for the container and all subgraph nodes so UIs see them queued again.
        state_events.append((copy.deepcopy(record), copy.deepcopy(container_node)))
        for node in frame_state.nodes.values():
            state_events.append((copy.deepcopy(record), copy.deepcopy(node)))
    return collect_ready_for_frame(record, frame_state, state_events=state_events)


def build_dispatch_request(
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
    worker_names = {
        ref.get("workerName") or ref.get("worker_name")
        for ref in resource_refs
        if ref.get("workerName") or ref.get("worker_name")
    }
    preferred_worker_name = None
    if len(worker_names) == 1:
        preferred_worker_name = next(iter(worker_names))
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
        preferred_worker_name=preferred_worker_name,
        host_node_id=host_node_id,
        middleware_chain=middleware_chain,
        chain_index=chain_index,
    )
