"""Publish helpers for run registry SSE events."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from scheduler_api.infra.sse import event_publisher
from scheduler_api.infra.sse.mappers import (
    node_result_delta_envelope,
    node_result_snapshot_envelope,
    node_state_envelope,
    run_snapshot_envelope,
    run_state_envelope,
)

from .format import (
    extract_node_message,
    extract_node_progress,
    extract_node_stage,
)
from scheduler_api.domain.models import NodeState, RunRecord, _utc_now

LOGGER = logging.getLogger(__name__)


async def publish_run_state(record: RunRecord) -> None:
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


async def publish_run_snapshot(record: RunRecord) -> None:
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


async def publish_node_state(record: RunRecord, node: NodeState) -> None:
    if not record.client_id:
        return
    progress = extract_node_progress(node)
    message = extract_node_message(node)
    stage = extract_node_stage(node)
    error_payload = node.error.to_dict() if node.error else None
    occurred_at = _utc_now()
    envelope = node_state_envelope(
        tenant=record.tenant,
        client_session_id=record.client_id,
        run_id=record.run_id,
        node_id=node.node_id,
        stage=stage,
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


async def publish_node_snapshot(
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


async def publish_node_result_delta(
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
