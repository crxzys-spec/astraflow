"""Pending middleware.next request helpers."""

from __future__ import annotations

from datetime import datetime
from typing import Callable, Dict, List, Optional, Tuple

from shared.models.biz.exec.next.response import ExecMiddlewareNextResponse
from shared.models.biz.exec.result import ExecResultPayload

from ..domain.models import NodeState

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


def resolve_next_response_worker(
    pending_next_requests: PendingNextRequests,
    request_id: str,
    *,
    utc_now: Callable[[], datetime],
) -> Optional[str]:
    entry = pending_next_requests.pop(request_id, None)
    if not entry:
        return None
    _, worker_instance_id, worker_name, deadline, _, _, _ = entry
    if deadline and utc_now() > deadline:
        return None
    return worker_instance_id or worker_name


def collect_expired_next_requests(
    pending_next_requests: PendingNextRequests,
    *,
    utc_now: Callable[[], datetime],
) -> Tuple[
    List[Tuple[str, str, str, Optional[str], Optional[str]]],
    PendingNextRequests,
]:
    now = utc_now()
    expired: List[Tuple[str, str, str, Optional[str], Optional[str]]] = []
    remaining: PendingNextRequests = {}
    for req_id, (
        run_id,
        worker_instance_id,
        worker_name,
        deadline,
        node_id,
        middleware_id,
        target_task_id,
    ) in pending_next_requests.items():
        if deadline and now > deadline:
            if worker_instance_id or worker_name:
                expired.append(
                    (
                        req_id,
                        worker_instance_id or worker_name or "",
                        run_id,
                        node_id,
                        middleware_id,
                    )
                )
        else:
            remaining[req_id] = (
                run_id,
                worker_instance_id,
                worker_name,
                deadline,
                node_id,
                middleware_id,
                target_task_id,
            )
    return expired, remaining


def finalise_pending_next(
    pending_next_requests: PendingNextRequests,
    payload: ExecResultPayload,
    node_state: NodeState,
    *,
    status: str,
) -> List[Tuple[Optional[str], ExecMiddlewareNextResponse]]:
    """Send a terminal next_response for any middleware.next waiting on this task."""
    responses: List[Tuple[Optional[str], ExecMiddlewareNextResponse]] = []
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
        if target_task_id == node_state.task_id and run_id == payload.run_id
    ]
    for req_id, worker_instance_id, run_id, node_id, middleware_id in pending_next_to_clear:
        pending_next_requests.pop(req_id, None)
        err_body = None
        if payload.error:
            err_body = {"code": payload.error.code, "message": payload.error.message}
        elif status != "succeeded":
            err_body = {"code": f"next_{status}", "message": f"target {node_state.node_id} status {status}"}
        resp = ExecMiddlewareNextResponse(
            requestId=req_id,
            runId=run_id,
            nodeId=node_id or "",
            middlewareId=middleware_id or "",
            result=node_state.result,
            error=err_body,
        )
        responses.append((worker_instance_id, resp))
    return responses
