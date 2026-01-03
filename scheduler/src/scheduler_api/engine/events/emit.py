"""Publish queue helpers for run registry events."""

from __future__ import annotations

from typing import Any, Awaitable, Callable, Dict, Iterable, List, Optional, Set, Tuple

from scheduler_api.domain.models import NodeState, RunRecord
from .publish import (
    publish_node_result_delta,
    publish_node_snapshot,
    publish_node_state,
    publish_run_snapshot,
    publish_run_state,
)


PublishNodeState = Callable[[RunRecord, NodeState], Awaitable[None]]
PublishNodeSnapshot = Callable[..., Awaitable[None]]
PublishRunState = Callable[[RunRecord], Awaitable[None]]
PublishRunSnapshot = Callable[[RunRecord], Awaitable[None]]
PublishNodeResultDelta = Callable[..., Awaitable[None]]


class RunRegistryEmitter:
    def __init__(
        self,
        *,
        publish_node_state: PublishNodeState,
        publish_node_snapshot: PublishNodeSnapshot,
        publish_run_state: PublishRunState,
        publish_run_snapshot: PublishRunSnapshot,
        publish_node_result_delta: PublishNodeResultDelta,
    ) -> None:
        self._publish_node_state = publish_node_state
        self._publish_node_snapshot = publish_node_snapshot
        self._publish_run_state = publish_run_state
        self._publish_run_snapshot = publish_run_snapshot
        self._publish_node_result_delta = publish_node_result_delta

    def enqueue_node_state(
        self,
        tasks: List[Awaitable[Any]],
        record: RunRecord,
        node: NodeState,
    ) -> None:
        enqueue_node_state(tasks, self._publish_node_state, record, node)

    def enqueue_node_snapshot(
        self,
        tasks: List[Awaitable[Any]],
        record: RunRecord,
        node: NodeState,
        *,
        complete: bool,
    ) -> None:
        enqueue_node_snapshot(
            tasks,
            self._publish_node_snapshot,
            record,
            node,
            complete=complete,
        )

    def enqueue_node_state_and_snapshot(
        self,
        tasks: List[Awaitable[Any]],
        record: RunRecord,
        node: NodeState,
        *,
        complete: bool,
    ) -> None:
        enqueue_node_state_and_snapshot(
            tasks,
            self._publish_node_state,
            self._publish_node_snapshot,
            record,
            node,
            complete=complete,
        )

    def enqueue_run_state(
        self,
        tasks: List[Awaitable[Any]],
        record: RunRecord,
    ) -> None:
        enqueue_run_state(tasks, self._publish_run_state, record)

    def enqueue_run_state_if_changed(
        self,
        tasks: List[Awaitable[Any]],
        record: RunRecord,
        *,
        previous_status: str,
    ) -> None:
        enqueue_run_state_if_changed(
            tasks,
            self._publish_run_state,
            record,
            previous_status=previous_status,
        )

    def enqueue_run_snapshot(
        self,
        tasks: List[Awaitable[Any]],
        record: RunRecord,
    ) -> None:
        enqueue_run_snapshot(tasks, self._publish_run_snapshot, record)

    def enqueue_state_events(
        self,
        tasks: List[Awaitable[Any]],
        state_events: Iterable[Tuple[RunRecord, NodeState]],
    ) -> None:
        enqueue_state_events(
            tasks,
            self._publish_node_state,
            self._publish_run_snapshot,
            state_events,
        )

    def enqueue_chunk_result_deltas(
        self,
        tasks: List[Awaitable[Any]],
        record: RunRecord,
        node: NodeState,
        chunk_events: Iterable[Dict[str, Any]],
    ) -> None:
        enqueue_chunk_result_deltas(
            tasks,
            self._publish_node_result_delta,
            record,
            node,
            chunk_events,
        )

    def enqueue_result_deltas(
        self,
        tasks: List[Awaitable[Any]],
        record: RunRecord,
        node: NodeState,
        result_deltas: Iterable[Dict[str, Any]],
    ) -> None:
        enqueue_result_deltas(
            tasks,
            self._publish_node_result_delta,
            record,
            node,
            result_deltas,
        )


def build_run_registry_emitter() -> RunRegistryEmitter:
    return RunRegistryEmitter(
        publish_node_state=publish_node_state,
        publish_node_snapshot=publish_node_snapshot,
        publish_run_state=publish_run_state,
        publish_run_snapshot=publish_run_snapshot,
        publish_node_result_delta=publish_node_result_delta,
    )


def build_run_state_tasks(
    emitter: RunRegistryEmitter,
    record: RunRecord,
) -> List[Awaitable[Any]]:
    tasks: List[Awaitable[Any]] = []
    emitter.enqueue_run_state(tasks, record)
    emitter.enqueue_run_snapshot(tasks, record)
    return tasks


def build_state_event_tasks(
    emitter: RunRegistryEmitter,
    state_events: Iterable[Tuple[RunRecord, NodeState]],
) -> List[Awaitable[Any]]:
    tasks: List[Awaitable[Any]] = []
    emitter.enqueue_state_events(tasks, state_events)
    return tasks


def build_node_state_tasks(
    emitter: RunRegistryEmitter,
    record: RunRecord,
    node: NodeState,
    *,
    previous_status: str,
) -> List[Awaitable[Any]]:
    tasks: List[Awaitable[Any]] = []
    emitter.enqueue_node_state(tasks, record, node)
    emitter.enqueue_run_state_if_changed(
        tasks,
        record,
        previous_status=previous_status,
    )
    emitter.enqueue_run_snapshot(tasks, record)
    return tasks


def build_record_result_tasks(
    emitter: RunRegistryEmitter,
    outcome: Any,
    *,
    final_statuses: Set[str],
) -> List[Awaitable[Any]]:
    tasks: List[Awaitable[Any]] = []
    emitter.enqueue_node_state_and_snapshot(
        tasks,
        outcome.record_snapshot,
        outcome.node_snapshot,
        complete=outcome.status in final_statuses,
    )
    if outcome.host_snapshot:
        emitter.enqueue_node_state_and_snapshot(
            tasks,
            outcome.record_snapshot,
            outcome.host_snapshot,
            complete=outcome.status in final_statuses,
        )
    if outcome.container_snapshot:
        emitter.enqueue_node_state_and_snapshot(
            tasks,
            outcome.record_snapshot,
            outcome.container_snapshot,
            complete=True,
        )
    emitter.enqueue_run_state_if_changed(
        tasks,
        outcome.record_snapshot,
        previous_status=outcome.previous_status,
    )
    emitter.enqueue_run_snapshot(tasks, outcome.record_snapshot)
    if outcome.state_events:
        emitter.enqueue_state_events(tasks, outcome.state_events)
    return tasks


def build_feedback_tasks(
    emitter: RunRegistryEmitter,
    outcome: Any,
) -> List[Awaitable[Any]]:
    tasks: List[Awaitable[Any]] = []
    if outcome.publish_node_state:
        emitter.enqueue_node_state_and_snapshot(
            tasks,
            outcome.record_snapshot,
            outcome.node_snapshot,
            complete=False,
        )
    if outcome.chunk_events and outcome.record_snapshot:
        node_for_delta = (
            outcome.node_snapshot
            or outcome.record_snapshot.nodes.get(outcome.node_state.node_id)
            or outcome.node_state
        )
        emitter.enqueue_chunk_result_deltas(
            tasks,
            outcome.record_snapshot,
            node_for_delta,
            outcome.chunk_events,
        )
    if outcome.result_deltas and outcome.record_snapshot:
        node_for_delta = (
            outcome.node_snapshot
            or outcome.record_snapshot.nodes.get(outcome.node_state.node_id)
            or outcome.node_state
        )
        emitter.enqueue_result_deltas(
            tasks,
            outcome.record_snapshot,
            node_for_delta,
            outcome.result_deltas,
        )
    return tasks


def build_next_request_tasks(
    emitter: RunRegistryEmitter,
    outcome: Any,
) -> List[Awaitable[Any]]:
    tasks: List[Awaitable[Any]] = []
    emitter.enqueue_state_events(tasks, outcome.state_events)
    if outcome.record_snapshot and outcome.node_snapshot:
        emitter.enqueue_node_state(
            tasks,
            outcome.record_snapshot,
            outcome.node_snapshot,
        )
        emitter.enqueue_run_snapshot(
            tasks,
            outcome.record_snapshot,
        )
    return tasks


def build_command_error_tasks(
    emitter: RunRegistryEmitter,
    outcome: Any,
) -> List[Awaitable[Any]]:
    tasks: List[Awaitable[Any]] = []
    if outcome.node_snapshot is not None:
        emitter.enqueue_node_state(
            tasks,
            outcome.record_snapshot,
            outcome.node_snapshot,
        )
    if outcome.container_snapshot:
        emitter.enqueue_node_state(
            tasks,
            outcome.record_snapshot,
            outcome.container_snapshot,
        )
    emitter.enqueue_run_state_if_changed(
        tasks,
        outcome.record_snapshot,
        previous_status=outcome.previous_status,
    )
    emitter.enqueue_run_snapshot(tasks, outcome.record_snapshot)
    return tasks


def enqueue_node_state(
    tasks: List[Awaitable[Any]],
    publish_node_state: PublishNodeState,
    record: RunRecord,
    node: NodeState,
) -> None:
    tasks.append(publish_node_state(record, node))


def enqueue_node_snapshot(
    tasks: List[Awaitable[Any]],
    publish_node_snapshot: PublishNodeSnapshot,
    record: RunRecord,
    node: NodeState,
    *,
    complete: bool,
) -> None:
    tasks.append(publish_node_snapshot(record, node, complete=complete))


def enqueue_node_state_and_snapshot(
    tasks: List[Awaitable[Any]],
    publish_node_state: PublishNodeState,
    publish_node_snapshot: PublishNodeSnapshot,
    record: RunRecord,
    node: NodeState,
    *,
    complete: bool,
) -> None:
    enqueue_node_state(tasks, publish_node_state, record, node)
    enqueue_node_snapshot(tasks, publish_node_snapshot, record, node, complete=complete)


def enqueue_run_state(
    tasks: List[Awaitable[Any]],
    publish_run_state: PublishRunState,
    record: RunRecord,
) -> None:
    tasks.append(publish_run_state(record))


def enqueue_run_state_if_changed(
    tasks: List[Awaitable[Any]],
    publish_run_state: PublishRunState,
    record: RunRecord,
    *,
    previous_status: str,
) -> None:
    if record.status != previous_status:
        tasks.append(publish_run_state(record))


def enqueue_run_snapshot(
    tasks: List[Awaitable[Any]],
    publish_run_snapshot: PublishRunSnapshot,
    record: RunRecord,
) -> None:
    tasks.append(publish_run_snapshot(record))


def enqueue_state_events(
    tasks: List[Awaitable[Any]],
    publish_node_state: PublishNodeState,
    publish_run_snapshot: PublishRunSnapshot,
    state_events: Iterable[Tuple[RunRecord, NodeState]],
) -> None:
    for record_snapshot, node_snapshot in state_events:
        tasks.append(publish_node_state(record_snapshot, node_snapshot))
        tasks.append(publish_run_snapshot(record_snapshot))


def enqueue_chunk_result_deltas(
    tasks: List[Awaitable[Any]],
    publish_node_result_delta: PublishNodeResultDelta,
    record: RunRecord,
    node: NodeState,
    chunk_events: Iterable[Dict[str, Any]],
) -> None:
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
            publish_node_result_delta(
                record,
                node,
                revision=event["revision"],
                sequence=event["sequence"],
                operation="append",
                path=f"/channels/{channel}" if channel else None,
                payload=payload_body or None,
                chunk_meta=chunk_meta or None,
                terminal=terminal,
            )
        )


def enqueue_result_deltas(
    tasks: List[Awaitable[Any]],
    publish_node_result_delta: PublishNodeResultDelta,
    record: RunRecord,
    node: NodeState,
    result_deltas: Iterable[Dict[str, Any]],
) -> None:
    for delta in result_deltas:
        operation = delta["operation"]
        value = delta.get("value")
        payload_body = {"value": value} if operation != "remove" else None
        tasks.append(
            publish_node_result_delta(
                record,
                node,
                revision=delta["revision"],
                sequence=delta["sequence"],
                operation=operation,
                path=delta["path"],
                payload=payload_body,
                chunk_meta=None,
                terminal=False,
            )
        )
