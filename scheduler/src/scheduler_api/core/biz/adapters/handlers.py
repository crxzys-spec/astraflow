"""Business handlers for scheduler control-plane envelopes."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Callable, Optional
from uuid import uuid4

from shared.models.biz.exec.error import ExecErrorPayload
from shared.models.biz.exec.feedback import ExecFeedbackPayload
from shared.models.biz.exec.next.request import ExecMiddlewareNextRequest
from shared.models.biz.exec.next.response import ExecMiddlewareNextResponse
from shared.models.biz.exec.result import ExecResultPayload
from shared.models.biz.pkg.event import PackageEvent
from shared.models.session import Role, Sender, WsEnvelope

from ..engine import status
from ..facade import biz_facade
from scheduler_api.core.network.server import ControlPlaneServer
from scheduler_api.core.network.manager import WorkerSession

LOGGER = logging.getLogger(__name__)
POLL_INTERVAL_SECONDS = 1.0


def register_handlers(server: ControlPlaneServer) -> None:
    async def _on_exec_result(envelope: WsEnvelope, session) -> None:
        await _handle_exec_result(server, envelope, session)

    async def _on_exec_feedback(envelope: WsEnvelope, session) -> None:
        await _handle_exec_feedback(envelope)

    async def _on_exec_next_request(envelope: WsEnvelope, session) -> None:
        await _handle_exec_next_request(server, envelope, session)

    async def _on_exec_next_response(envelope: WsEnvelope, session) -> None:
        await _handle_exec_next_response(server, envelope)

    async def _on_exec_error(envelope: WsEnvelope, session) -> None:
        await _handle_exec_error(envelope)

    async def _on_pkg_event(envelope: WsEnvelope, session) -> None:
        await _handle_pkg_event(envelope)

    async def _on_control_ack(envelope: WsEnvelope, session) -> None:
        await _handle_control_ack(envelope)

    server.register_handler("biz.exec.result", _on_exec_result)
    server.register_handler("biz.exec.feedback", _on_exec_feedback)
    server.register_handler("biz.exec.next.request", _on_exec_next_request)
    server.register_handler("biz.exec.next.response", _on_exec_next_response)
    server.register_handler("biz.exec.error", _on_exec_error)
    server.register_handler("biz.pkg.event", _on_pkg_event)
    server.register_handler("control.ack", _on_control_ack)

    server.add_connection_task(lambda session_provider: _poll_expired_next(server, session_provider))


async def _process_result(server: ControlPlaneServer, envelope: WsEnvelope, result: ExecResultPayload) -> None:
    LOGGER.debug(
        "Processing result envelope id=%s corr=%s run=%s status=%s",
        envelope.id,
        envelope.corr,
        result.run_id,
        result.status.value,
    )
    try:
        record, _ready, next_responses = await biz_facade.record_result(result)
        if next_responses:
            for target_worker, resp in next_responses:
                if not target_worker:
                    continue
                resp_envelope = WsEnvelope(
                    type="biz.exec.next.response",
                    id=str(uuid4()),
                    ts=datetime.now(timezone.utc),
                    corr=resp.requestId,
                    seq=None,
                    tenant=record.tenant if record else "default",
                    sender=Sender(role=Role.scheduler, id=server.scheduler_id),
                    payload=resp.model_dump(by_alias=True, exclude_none=True),
                )
                await server.send_envelope(target_worker, resp_envelope)
        artifacts_count = len(record.artifacts) if record else 0
        LOGGER.info(
            "Result received corr=%s status=%s run=%s artifacts=%s",
            envelope.corr,
            result.status.value,
            result.run_id,
            artifacts_count,
        )
    except Exception:  # noqa: BLE001
        LOGGER.exception(
            "Failed to process result corr=%s run=%s",
            envelope.corr,
            result.run_id,
        )
    finally:
        LOGGER.debug(
            "Completed processing result envelope id=%s corr=%s run=%s",
            envelope.id,
            envelope.corr,
            result.run_id,
        )


async def _handle_exec_result(server: ControlPlaneServer, envelope: WsEnvelope, session) -> None:
    result = ExecResultPayload.model_validate(envelope.payload)
    LOGGER.info(
        "Result frame received id=%s request_ack=%s corr=%s run=%s",
        envelope.id,
        envelope.ack.request if envelope.ack else None,
        envelope.corr,
        result.run_id,
    )
    asyncio.create_task(_process_result(server, envelope, result))


async def _handle_exec_feedback(envelope: WsEnvelope) -> None:
    feedback = ExecFeedbackPayload.model_validate(envelope.payload)
    await biz_facade.record_feedback(feedback)


async def _handle_exec_next_request(server: ControlPlaneServer, envelope: WsEnvelope, session) -> None:
    next_req = ExecMiddlewareNextRequest.model_validate(envelope.payload)
    LOGGER.info(
        "Received biz.exec.next.request run=%s node=%s middleware=%s request=%s",
        next_req.runId,
        next_req.nodeId,
        next_req.middlewareId,
        next_req.requestId,
    )
    try:
        ready, error = await biz_facade.handle_next_request(
            next_req,
            worker_name=session.worker_name if session else None,
            worker_instance_id=session.worker_instance_id if session else None,
        )
        if not ready and session:
            message = status.get_next_error_message(error or "next_unavailable")
            err_payload = ExecMiddlewareNextResponse(
                requestId=next_req.requestId,
                runId=next_req.runId,
                nodeId=next_req.nodeId,
                middlewareId=next_req.middlewareId,
                error={"code": error or "next_unavailable", "message": message},
            )
            resp_envelope = WsEnvelope(
                type="biz.exec.next.response",
                id=str(uuid4()),
                ts=datetime.now(timezone.utc),
                corr=next_req.requestId,
                seq=None,
                tenant=envelope.tenant,
                sender=Sender(role=Role.scheduler, id=server.scheduler_id),
                payload=err_payload.model_dump(by_alias=True, exclude_none=True),
            )
            await server.send_envelope(session, resp_envelope)
    except Exception:  # noqa: BLE001
        LOGGER.exception(
            "Failed to handle biz.exec.next.request run=%s middleware=%s req=%s",
            next_req.runId,
            next_req.middlewareId,
            next_req.requestId,
        )


async def _handle_exec_next_response(server: ControlPlaneServer, envelope: WsEnvelope) -> None:
    next_resp = ExecMiddlewareNextResponse.model_validate(envelope.payload)
    LOGGER.info(
        "Received biz.exec.next.response run=%s node=%s middleware=%s request=%s",
        next_resp.runId,
        next_resp.nodeId,
        next_resp.middlewareId,
        next_resp.requestId,
    )
    try:
        target_worker = await biz_facade.resolve_next_response_worker(next_resp.requestId)
        if not target_worker:
            LOGGER.warning(
                "No pending middleware next waiter for request=%s run=%s",
                next_resp.requestId,
                next_resp.runId,
            )
        else:
            resp_envelope = WsEnvelope(
                type="biz.exec.next.response",
                id=str(uuid4()),
                ts=datetime.now(timezone.utc),
                corr=next_resp.requestId,
                seq=None,
                tenant=envelope.tenant,
                sender=Sender(role=Role.scheduler, id=server.scheduler_id),
                payload=next_resp.model_dump(by_alias=True, exclude_none=True),
            )
            await server.send_envelope(target_worker, resp_envelope)
    except Exception:  # noqa: BLE001
        LOGGER.exception(
            "Failed to route biz.exec.next.response req=%s run=%s",
            next_resp.requestId,
            next_resp.runId,
        )


async def _handle_exec_error(envelope: WsEnvelope) -> None:
    error_payload = ExecErrorPayload.model_validate(envelope.payload)
    details = error_payload.context.details if error_payload.context else {}
    run_id = None
    if details:
        run_id = details.get("run_id") or details.get("runId") or details.get("run")
    if error_payload.code == "E.CMD.CONCURRENCY_VIOLATION":
        LOGGER.info(
            "Worker reported concurrency violation corr=%s run=%s node=%s; keeping existing task in-flight",
            envelope.corr,
            run_id,
            details.get("node_id") if isinstance(details, dict) else None,
        )
    elif error_payload.code == "E.RUNNER.CANCELLED":
        node_id = details.get("node_id") if isinstance(details, dict) else None
        record = await biz_facade.reset_after_worker_cancel(
            run_id,
            node_id=node_id,
            task_id=envelope.corr,
        )
        LOGGER.info(
            "Worker reported cancellation corr=%s run=%s node=%s; node reset for retry",
            envelope.corr,
            run_id,
            node_id,
        )
    else:
        _, _ = await biz_facade.record_command_error(
            payload=error_payload,
            run_id=run_id,
            task_id=envelope.corr,
        )
        LOGGER.warning(
            "Worker command error corr=%s code=%s message=%s",
            envelope.corr,
            error_payload.code,
            error_payload.message,
        )


async def _handle_pkg_event(envelope: WsEnvelope) -> None:
    PackageEvent.model_validate(envelope.payload)
    LOGGER.info("Package event from worker: %s", envelope.payload)


async def _handle_control_ack(envelope: WsEnvelope) -> None:
    ack_id = envelope.ack.for_ if envelope.ack else None
    if ack_id:
        await biz_facade.register_ack(ack_id)
    else:
        LOGGER.debug("Ack received without dispatch reference")


async def _poll_expired_next(
    server: ControlPlaneServer,
    session_provider: Callable[[], Optional[WorkerSession]],
) -> None:
    while True:
        try:
            await asyncio.sleep(POLL_INTERVAL_SECONDS)
            try:
                expired = await biz_facade.collect_expired_next_requests()
                for request_id, target_worker, run_id, node_id, middleware_id in expired:
                    session = session_provider()
                    tenant = session.tenant if session else "default"
                    resp_envelope = WsEnvelope(
                        type="biz.exec.next.response",
                        id=str(uuid4()),
                        ts=datetime.now(timezone.utc),
                        corr=request_id,
                        seq=None,
                        tenant=tenant,
                        sender=Sender(role=Role.scheduler, id=server.scheduler_id),
                        payload={
                            "requestId": request_id,
                            "runId": run_id,
                            "nodeId": node_id or "",
                            "middlewareId": middleware_id or "",
                            "error": {
                                "code": "next_timeout",
                                "message": status.get_next_error_message("next_timeout"),
                            },
                        },
                    )
                    await server.send_envelope(target_worker, resp_envelope)
            except Exception:
                LOGGER.exception("Failed to process expired middleware.next_request")
        except asyncio.CancelledError:
            break
