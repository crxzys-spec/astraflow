import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.encoders import jsonable_encoder

from shared.models.ws.envelope import Ack, Role, Sender, WsEnvelope
from shared.models.ws.error import ErrorPayload
from shared.models.ws.pkg.event import PackageEvent
from shared.models.ws.feedback import FeedbackPayload
from shared.models.ws.result import ResultPayload
from shared.models.ws.handshake import HandshakePayload
from shared.models.ws.heartbeat import HeartbeatPayload
from shared.models.ws.register import RegisterPayload
from shared.models.ws.next import NextRequestPayload, NextResponsePayload

from .manager import WorkerSession, worker_manager
from .run_registry import run_registry
from .orchestrator import run_orchestrator

logger = logging.getLogger(__name__)

router = APIRouter()
POLL_INTERVAL_SECONDS = 1.0


def _dump_envelope(envelope: WsEnvelope) -> str:
    payload = envelope.model_dump(by_alias=True, exclude_none=True)
    return json.dumps(jsonable_encoder(payload))


async def _maybe_ack(envelope: WsEnvelope, websocket: WebSocket, *, force: bool = False) -> None:
    requested = bool(envelope.ack and envelope.ack.request)
    logger.debug(
        "Evaluating ack for envelope id=%s type=%s requested=%s force=%s",
        envelope.id,
        envelope.type,
        requested,
        force,
    )
    if not force and not requested:
        return
    logger.debug(
        "Sending ack for envelope id=%s type=%s force=%s",
        envelope.id,
        envelope.type,
        force,
    )
    ack_envelope = WsEnvelope(
        type="ack",
        id=str(uuid4()),
        ts=datetime.now(timezone.utc),
        corr=envelope.corr,
        seq=None,
        tenant=envelope.tenant,
        sender=Sender(role=Role.scheduler, id=worker_manager.scheduler_id),
        ack=Ack(**{"for": envelope.id}) if envelope.id else None,
        payload={"ok": True, "for": envelope.id},
    )
    await websocket.send_text(_dump_envelope(ack_envelope))


async def _process_result(envelope: WsEnvelope, result: ResultPayload) -> None:
    logger.debug(
        "Processing result envelope id=%s corr=%s run=%s status=%s",
        envelope.id,
        envelope.corr,
        result.run_id,
        result.status.value,
    )
    try:
        record, ready, next_responses = await run_registry.record_result(result.run_id, result)
        if ready:
            await run_orchestrator.enqueue(ready)
        if next_responses:
            for target_worker, resp in next_responses:
                if not target_worker:
                    continue
                resp_envelope = WsEnvelope(
                    type="middleware.next_response",
                    id=str(uuid4()),
                    ts=datetime.now(timezone.utc),
                    corr=resp.request_id,
                    seq=None,
                    tenant=record.tenant if record else "default",
                    sender=Sender(role=Role.scheduler, id=worker_manager.scheduler_id),
                    payload=resp.model_dump(by_alias=True, exclude_none=True),
                )
                await worker_manager.send_envelope(target_worker, resp_envelope)
        artifacts_count = len(record.artifacts) if record else 0
        logger.info(
            "Result received corr=%s status=%s run=%s artifacts=%s",
            envelope.corr,
            result.status.value,
            result.run_id,
            artifacts_count,
        )
    except Exception:  # noqa: BLE001
        logger.exception(
            "Failed to process result corr=%s run=%s",
            envelope.corr,
            result.run_id,
        )
    finally:
        logger.debug(
            "Completed processing result envelope id=%s corr=%s run=%s",
            envelope.id,
            envelope.corr,
            result.run_id,
        )


@router.websocket("/ws/worker")
async def worker_control_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    session: Optional[WorkerSession] = None
    logger.info("Worker connection opened from %s", websocket.client)
    # background polling for expired next requests
    poll_task: Optional[asyncio.Task] = None
    async def _pump_expired_next() -> None:
        while True:
            await asyncio.sleep(POLL_INTERVAL_SECONDS)
            try:
                expired = await run_registry.collect_expired_next_requests()
                for request_id, target_worker, run_id, node_id, middleware_id in expired:
                    resp_envelope = WsEnvelope(
                        type="middleware.next_response",
                        id=str(uuid4()),
                        ts=datetime.now(timezone.utc),
                        corr=request_id,
                        seq=None,
                        tenant=session.tenant if session else "default",
                        sender=Sender(role=Role.scheduler, id=worker_manager.scheduler_id),
                        payload={
                            "requestId": request_id,
                            "runId": run_id,
                            "nodeId": node_id or "",
                            "middlewareId": middleware_id or "",
                            "error": {
                                "code": "next_timeout",
                                "message": run_registry.get_next_error_message("next_timeout"),
                            },
                        },
                    )
                    await worker_manager.send_envelope(target_worker, resp_envelope)
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Failed to process expired middleware.next_request")

    try:
        poll_task = asyncio.create_task(_pump_expired_next())
        while True:
            message = await websocket.receive_json()
            envelope = WsEnvelope.model_validate(message)
            message_type = envelope.type

            if message_type == "handshake":
                handshake = HandshakePayload.model_validate(envelope.payload)
                session = worker_manager.upsert_session(
                    worker_id=handshake.worker.id,
                    tenant=envelope.tenant,
                    version=handshake.worker.version,
                    hostname=handshake.worker.hostname,
                    websocket=websocket,
                )
                logger.info(
                    "Handshake received from worker %s (tenant=%s)",
                    session.worker_id,
                    session.tenant,
                )
                await _maybe_ack(envelope, websocket, force=True)

            elif message_type == "register":
                if not session:
                    logger.warning("Register received before handshake; closing connection")
                    await _maybe_ack(envelope, websocket, force=True)
                    await websocket.close(code=1011, reason="handshake required")
                    return
                register = RegisterPayload.model_validate(envelope.payload)
                worker_manager.update_registration(
                    session.worker_id,
                    capabilities=register.capabilities,
                    packages=register.packages,
                )
                logger.info("Worker %s registered %d packages", session.worker_id, len(register.packages))
                await _maybe_ack(envelope, websocket, force=True)

            elif message_type == "heartbeat":
                if session:
                    worker_manager.mark_heartbeat(session.worker_id)
                HeartbeatPayload.model_validate(envelope.payload)
                await _maybe_ack(envelope, websocket)

            elif message_type == "result":
                result = ResultPayload.model_validate(envelope.payload)
                logger.info(
                    "Result frame received id=%s request_ack=%s corr=%s run=%s",
                    envelope.id,
                    envelope.ack.request if envelope.ack else None,
                    envelope.corr,
                    result.run_id,
                )
                await _maybe_ack(envelope, websocket)
                asyncio.create_task(_process_result(envelope, result))

            elif message_type == "feedback":
                feedback = FeedbackPayload.model_validate(envelope.payload)
                await run_registry.record_feedback(feedback)
                await _maybe_ack(envelope, websocket)

            elif message_type == "middleware.next_request":
                next_req = NextRequestPayload.model_validate(envelope.payload)
                logger.info(
                    "Received middleware.next_request run=%s node=%s middleware=%s request=%s",
                    next_req.run_id,
                    next_req.node_id,
                    next_req.middleware_id,
                    next_req.request_id,
                )
                await _maybe_ack(envelope, websocket)
                try:
                    ready, error = await run_registry.handle_next_request(
                        next_req,
                        worker_id=session.worker_id if session else None,
                    )
                    if ready:
                        await run_orchestrator.enqueue(ready)
                    elif session:
                        message = run_registry.get_next_error_message(error or "next_unavailable")
                        err_payload = NextResponsePayload(
                            requestId=next_req.request_id,
                            runId=next_req.run_id,
                            nodeId=next_req.node_id,
                            middlewareId=next_req.middleware_id,
                            error={"code": error or "next_unavailable", "message": message},
                        )
                        resp_envelope = WsEnvelope(
                            type="middleware.next_response",
                            id=str(uuid4()),
                            ts=datetime.now(timezone.utc),
                            corr=next_req.request_id,
                            seq=None,
                            tenant=envelope.tenant,
                            sender=Sender(role=Role.scheduler, id=worker_manager.scheduler_id),
                            payload=err_payload.model_dump(by_alias=True, exclude_none=True),
                        )
                        await worker_manager.send_envelope(session.worker_id, resp_envelope)
                except Exception:  # noqa: BLE001
                    logger.exception(
                        "Failed to handle middleware.next_request run=%s middleware=%s req=%s",
                        next_req.run_id,
                        next_req.middleware_id,
                        next_req.request_id,
                    )

            elif message_type == "middleware.next_response":
                next_resp = NextResponsePayload.model_validate(envelope.payload)
                logger.info(
                    "Received middleware.next_response run=%s node=%s middleware=%s request=%s",
                    next_resp.run_id,
                    next_resp.node_id,
                    next_resp.middleware_id,
                    next_resp.request_id,
                )
                await _maybe_ack(envelope, websocket)
                try:
                    target_worker = await run_registry.resolve_next_response_worker(next_resp.request_id)
                    if not target_worker:
                        logger.warning(
                            "No pending middleware next waiter for request=%s run=%s",
                            next_resp.request_id,
                            next_resp.run_id,
                        )
                    else:
                        resp_envelope = WsEnvelope(
                            type="middleware.next_response",
                            id=str(uuid4()),
                            ts=datetime.now(timezone.utc),
                            corr=next_resp.request_id,
                            seq=None,
                            tenant=envelope.tenant,
                            sender=Sender(role=Role.scheduler, id=worker_manager.scheduler_id),
                            payload=next_resp.model_dump(by_alias=True, exclude_none=True),
                        )
                        await worker_manager.send_envelope(target_worker, resp_envelope)
                except Exception:  # noqa: BLE001
                    logger.exception(
                        "Failed to route middleware.next_response req=%s run=%s",
                        next_resp.request_id,
                        next_resp.run_id,
                    )

            elif message_type == "command.error":
                error_payload = ErrorPayload.model_validate(envelope.payload)
                details = error_payload.context.details if error_payload.context else {}
                run_id = None
                if details:
                    run_id = details.get("run_id") or details.get("runId") or details.get("run")
                record, _ = await run_registry.record_command_error(
                    payload=error_payload,
                    run_id=run_id,
                    task_id=envelope.corr,
                )
                logger.warning(
                    "Worker command error corr=%s code=%s message=%s",
                    envelope.corr,
                    error_payload.code,
                    error_payload.message,
                )
                await _maybe_ack(envelope, websocket)

            elif message_type == "pkg.event":
                PackageEvent.model_validate(envelope.payload)
                logger.info("Package event from worker: %s", envelope.payload)
                await _maybe_ack(envelope, websocket)

            elif message_type == "ack":
                ack_id = envelope.ack.for_ if envelope.ack else None
                if ack_id:
                    await run_orchestrator.register_ack(ack_id)
                else:
                    logger.debug("Ack received without dispatch reference")

            else:
                logger.warning("Unhandled message type %s", message_type)

    except WebSocketDisconnect:
        logger.info("Worker connection closed")
    except Exception:
        logger.exception("Worker control-plane encountered an error; closing connection")
        await websocket.close(code=1011, reason="internal error")
    finally:
        if poll_task:
            poll_task.cancel()
        if session:
            worker_manager.remove_session(session.worker_id)
            logger.info("Worker %s removed from session registry", session.worker_id)
