"""Lookup helpers for run records and frames."""

from __future__ import annotations

from typing import Dict, Optional, Tuple

from ..domain.models import FrameDefinition, FrameRuntimeState, NodeState, RunRecord


def resolve_node_state(
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


def find_node_by_dispatch(
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


def find_frame_for_container(
    record: RunRecord,
    *,
    container_node_id: str,
    parent_frame_id: Optional[str],
) -> Optional[FrameDefinition]:
    if not record.frames_by_parent:
        return None
    return record.frames_by_parent.get((parent_frame_id, container_node_id))


def get_parent_graph(
    record: RunRecord,
    parent_frame_id: Optional[str],
) -> Tuple[Dict[str, NodeState], Optional[FrameRuntimeState]]:
    if parent_frame_id is None:
        return record.nodes, None
    parent_frame = record.active_frames.get(parent_frame_id)
    if parent_frame:
        return parent_frame.nodes, parent_frame
    return record.nodes, None
