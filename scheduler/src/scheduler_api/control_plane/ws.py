import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.encoders import jsonable_encoder
from websockets.exceptions import ConnectionClosedOK, ConnectionClosedError

from shared.models.session import (
    Ack,
    AckPayload,
    HandshakePayload,
    HeartbeatPayload,
    RegisterPayload,
    Role,
    Sender,
    SessionAcceptPayload,
    SessionResetPayload,
    SessionResumePayload,
    WsEnvelope,
)
from shared.models.session.handshake import Mode
from shared.models.biz.exec.error import ExecErrorPayload
from shared.models.biz.exec.feedback import ExecFeedbackPayload
from shared.models.biz.exec.result import ExecResultPayload
from shared.models.biz.exec.next.request import ExecMiddlewareNextRequest
from shared.models.biz.exec.next.response import ExecMiddlewareNextResponse
from shared.models.biz.pkg.event import PackageEvent

from .manager import WorkerSession, worker_manager
from .run_registry import run_registry
from .orchestrator import run_orchestrator
from .session_tokens import issue_session_token, validate_session_token
from scheduler_api.config.settings import get_settings

logger = logging.getLogger(__name__)

router = APIRouter()
POLL_INTERVAL_SECONDS = 1.0
settings = get_settings()


def _dump_envelope(envelope: WsEnvelope) -> str:
    payload = envelope.model_dump(by_alias=True, exclude_none=True)
    return json.dumps(jsonable_encoder(payload))


def _validate_worker_auth(handshake: HandshakePayload) -> tuple[bool, str, str]:
    auth = handshake.auth
    if auth.mode == Mode.token:
        if not auth.token:
            return False, "E.AUTH.MISSING_TOKEN", "Missing auth token"
        allowed = settings.allowed_worker_tokens()
        if allowed and auth.token not in allowed:
            return False, "E.AUTH.INVALID_TOKEN", "Invalid auth token"
        if not allowed:
            logger.warning("No worker auth tokens configured; accepting any token")
        return True, "", ""
    if auth.mode == Mode.mtls:
        if not auth.fingerprint:
            return False, "E.AUTH.MTLS_REQUIRED", "Missing mTLS fingerprint"
        return True, "", ""
    return False, "E.AUTH.MODE_UNSUPPORTED", "Unsupported auth mode"


async def _send_reset(websocket: WebSocket, envelope: WsEnvelope, *, code: str, reason: str) -> None:
    reset_payload = SessionResetPayload(code=code, reason=reason)
    reset_envelope = WsEnvelope(
        type="control.reset",
        id=str(uuid4()),
        ts=datetime.now(timezone.utc),
        corr=envelope.corr,
        seq=None,
        tenant=envelope.tenant,
        sender=Sender(role=Role.scheduler, id=worker_manager.scheduler_id),
        payload=reset_payload.model_dump(by_alias=True, exclude_none=True),
    )
    await websocket.send_text(_dump_envelope(reset_envelope))
    await websocket.close(code=1011, reason=reason)


def _build_session_accept(session: WorkerSession, *, tenant: str, resumed: bool) -> WsEnvelope:
    if not session.session_id:
        session.session_id = str(uuid4())
    token, expires_at = issue_session_token(
        session_id=session.session_id,
        worker_instance_id=session.worker_instance_id,
        tenant=tenant,
    )
    session.session_token = token
    session.session_expires_at = datetime.fromtimestamp(expires_at, tz=timezone.utc)
    payload = SessionAcceptPayload(
        session_id=session.session_id,
        session_token=token,
        expires_at=session.session_expires_at,
        resumed=resumed,
        worker_instance_id=session.worker_instance_id,
    )
    return WsEnvelope(
        type="control.session.accept",
        id=str(uuid4()),
        ts=datetime.now(timezone.utc),
        corr=None,
        seq=None,
        tenant=tenant,
        sender=Sender(role=Role.scheduler, id=worker_manager.scheduler_id),
        payload=payload.model_dump(by_alias=True, exclude_none=True),
    )


async def _maybe_ack(
    envelope: WsEnvelope,
    websocket: WebSocket,
    *,
    session: Optional[WorkerSession] = None,
    force: bool = False,
) -> None:
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
    include_for = requested
    logger.debug(
        "Sending ack for envelope id=%s type=%s force=%s",
        envelope.id,
        envelope.type,
        force,
    )
    payload: dict[str, object] = {"ok": True}
    if include_for and envelope.id:
        payload["for"] = envelope.id
    if session and session.recv_window:
        base_seq, bitmap, window = session.recv_window.ack_state()
        payload["ack_seq"] = base_seq
        payload["ack_bitmap"] = bitmap
        payload["recv_window"] = window
    ack_envelope = WsEnvelope(
        type="control.ack",
        id=str(uuid4()),
        ts=datetime.now(timezone.utc),
        corr=envelope.corr,
        seq=None,
        tenant=envelope.tenant,
        sender=Sender(role=Role.scheduler, id=worker_manager.scheduler_id),
        ack=Ack(**{"for": envelope.id}) if include_for and envelope.id else None,
        payload=payload,
    )
    try:
        await websocket.send_text(_dump_envelope(ack_envelope))
    except (ConnectionClosedOK, ConnectionClosedError):
        logger.debug(
            "Ack send skipped: websocket already closed id=%s type=%s",
            envelope.id,
            envelope.type,
        )


async def _process_result(envelope: WsEnvelope, result: ExecResultPayload) -> None:
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
                    type="biz.exec.next.response",
                    id=str(uuid4()),
                    ts=datetime.now(timezone.utc),
                    corr=resp.requestId,
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


async def _handle_biz_envelope(envelope: WsEnvelope, *, session: Optional[WorkerSession]) -> None:
    message_type = envelope.type

    if message_type == "biz.exec.result":
        result = ExecResultPayload.model_validate(envelope.payload)
        logger.info(
            "Result frame received id=%s request_ack=%s corr=%s run=%s",
            envelope.id,
            envelope.ack.request if envelope.ack else None,
            envelope.corr,
            result.run_id,
        )
        asyncio.create_task(_process_result(envelope, result))
        return

    if message_type == "biz.exec.feedback":
        feedback = ExecFeedbackPayload.model_validate(envelope.payload)
        await run_registry.record_feedback(feedback)
        return

    if message_type == "biz.exec.next.request":
        next_req = ExecMiddlewareNextRequest.model_validate(envelope.payload)
        logger.info(
            "Received biz.exec.next.request run=%s node=%s middleware=%s request=%s",
            next_req.runId,
            next_req.nodeId,
            next_req.middlewareId,
            next_req.requestId,
        )
        try:
            ready, error = await run_registry.handle_next_request(
                next_req,
                worker_name=session.worker_name if session else None,
                worker_instance_id=session.worker_instance_id if session else None,
            )
            if ready:
                await run_orchestrator.enqueue(ready)
            elif session:
                message = run_registry.get_next_error_message(error or "next_unavailable")
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
                    sender=Sender(role=Role.scheduler, id=worker_manager.scheduler_id),
                    payload=err_payload.model_dump(by_alias=True, exclude_none=True),
                )
                await worker_manager.send_envelope(session, resp_envelope)
        except Exception:  # noqa: BLE001
            logger.exception(
                "Failed to handle biz.exec.next.request run=%s middleware=%s req=%s",
                next_req.runId,
                next_req.middlewareId,
                next_req.requestId,
            )
        return

    if message_type == "biz.exec.next.response":
        next_resp = ExecMiddlewareNextResponse.model_validate(envelope.payload)
        logger.info(
            "Received biz.exec.next.response run=%s node=%s middleware=%s request=%s",
            next_resp.runId,
            next_resp.nodeId,
            next_resp.middlewareId,
            next_resp.requestId,
        )
        try:
            target_worker = await run_registry.resolve_next_response_worker(next_resp.requestId)
            if not target_worker:
                logger.warning(
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
                    sender=Sender(role=Role.scheduler, id=worker_manager.scheduler_id),
                    payload=next_resp.model_dump(by_alias=True, exclude_none=True),
                )
                await worker_manager.send_envelope(target_worker, resp_envelope)
        except Exception:  # noqa: BLE001
            logger.exception(
                "Failed to route biz.exec.next.response req=%s run=%s",
                next_resp.requestId,
                next_resp.runId,
            )
        return

    if message_type == "biz.exec.error":
        error_payload = ExecErrorPayload.model_validate(envelope.payload)
        details = error_payload.context.details if error_payload.context else {}
        run_id = None
        if details:
            run_id = details.get("run_id") or details.get("runId") or details.get("run")
        if error_payload.code == "E.CMD.CONCURRENCY_VIOLATION":
            logger.info(
                "Worker reported concurrency violation corr=%s run=%s node=%s; keeping existing task in-flight",
                envelope.corr,
                run_id,
                details.get("node_id") if isinstance(details, dict) else None,
            )
        elif error_payload.code == "E.RUNNER.CANCELLED":
            node_id = details.get("node_id") if isinstance(details, dict) else None
            record = await run_registry.reset_after_worker_cancel(
                run_id,
                node_id=node_id,
                task_id=envelope.corr,
            )
            if record:
                ready = await run_registry.collect_ready_nodes(record.run_id)
                if ready:
                    await run_orchestrator.enqueue(ready)
            logger.info(
                "Worker reported cancellation corr=%s run=%s node=%s; node reset for retry",
                envelope.corr,
                run_id,
                node_id,
            )
        else:
            _, _ = await run_registry.record_command_error(
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
        return

    if message_type == "biz.pkg.event":
        PackageEvent.model_validate(envelope.payload)
        logger.info("Package event from worker: %s", envelope.payload)
        return

    logger.warning("Unhandled message type %s", message_type)


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
                        type="biz.exec.next.response",
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

            if message_type == "control.resume":
                resume = SessionResumePayload.model_validate(envelope.payload)
                worker_instance_id = envelope.sender.id
                session = worker_manager.get_session(worker_instance_id, worker_name="")
                if not session:
                    await _send_reset(websocket, envelope, code="E.SESSION.UNKNOWN", reason="Unknown session")
                    return
                if session.tenant != envelope.tenant:
                    await _send_reset(websocket, envelope, code="E.SESSION.TENANT_MISMATCH", reason="Tenant mismatch")
                    return
                if not session.registered or not session.session_id:
                    await _send_reset(websocket, envelope, code="E.SESSION.NOT_REGISTERED", reason="Session not registered")
                    return
                if session.session_id != resume.session_id:
                    await _send_reset(websocket, envelope, code="E.SESSION.MISMATCH", reason="Session id mismatch")
                    return
                if not validate_session_token(
                    resume.session_token,
                    session_id=resume.session_id,
                    worker_instance_id=session.worker_instance_id,
                    tenant=envelope.tenant,
                ):
                    await _send_reset(websocket, envelope, code="E.SESSION.INVALID_TOKEN", reason="Invalid session token")
                    return
                bound = worker_manager.bind_session(worker_instance_id, session.worker_name, websocket)
                if not bound:
                    await _send_reset(websocket, envelope, code="E.SESSION.UNKNOWN", reason="Unknown session")
                    return
                session = bound
                session.authenticated = True
                session.registered = True
                await _maybe_ack(envelope, websocket, session=session, force=True)
                accept_envelope = _build_session_accept(session, tenant=envelope.tenant, resumed=True)
                await websocket.send_text(_dump_envelope(accept_envelope))

            elif message_type == "control.handshake":
                handshake = HandshakePayload.model_validate(envelope.payload)
                worker_instance_id = handshake.worker.worker_instance_id or str(uuid4())
                ok, code, reason = _validate_worker_auth(handshake)
                if not ok:
                    await _send_reset(websocket, envelope, code=code, reason=reason)
                    return
                session = worker_manager.upsert_session(
                    worker_name=handshake.worker.worker_name,
                    worker_instance_id=worker_instance_id,
                    tenant=envelope.tenant,
                    version=handshake.worker.version,
                    hostname=handshake.worker.hostname,
                    websocket=websocket,
                )
                session.authenticated = True
                logger.info(
                    "Handshake received from worker %s (tenant=%s)",
                    session.worker_name,
                    session.tenant,
                )
                await _maybe_ack(envelope, websocket, session=session, force=True)

            elif message_type == "control.register":
                if not session:
                    logger.warning("Register received before handshake; closing connection")
                    await _send_reset(
                        websocket,
                        envelope,
                        code="E.AUTH.HANDSHAKE_REQUIRED",
                        reason="handshake required",
                    )
                    return
                if not session.authenticated:
                    await _send_reset(
                        websocket,
                        envelope,
                        code="E.AUTH.UNAUTHENTICATED",
                        reason="unauthenticated session",
                    )
                    return
                register = RegisterPayload.model_validate(envelope.payload)
                worker_manager.update_registration(
                    session.worker_instance_id,
                    session.worker_name,
                    capabilities=register.capabilities,
                    payload_types=register.payload_types or [],
                )
                session.registered = True
                logger.info("Worker %s registered payload types=%s", session.worker_name, register.payload_types or [])
                await _maybe_ack(envelope, websocket, session=session, force=True)
                accept_envelope = _build_session_accept(session, tenant=envelope.tenant, resumed=False)
                await websocket.send_text(_dump_envelope(accept_envelope))

            elif message_type == "control.heartbeat":
                if session:
                    worker_manager.mark_heartbeat(session.worker_instance_id, session.worker_name)
                HeartbeatPayload.model_validate(envelope.payload)
                await _maybe_ack(envelope, websocket, session=session)

            elif message_type == "control.ack":
                try:
                    ack_payload = AckPayload.model_validate(envelope.payload or {})
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Invalid ack payload: %s", exc)
                    ack_payload = None
                if session and ack_payload:
                    worker_manager.apply_session_ack(session, ack_payload)
                ack_id = envelope.ack.for_ if envelope.ack else None
                if ack_id:
                    await run_orchestrator.register_ack(ack_id)
                else:
                    logger.debug("Ack received without dispatch reference")

            else:
                if session and envelope.session_seq is not None and session.recv_window:
                    ready, accepted = session.recv_window.record(envelope.session_seq, envelope)
                    await _maybe_ack(envelope, websocket, session=session, force=True)
                    if not accepted:
                        offset = envelope.session_seq - session.recv_window.base_seq - 1
                        if envelope.session_seq in session.recv_window.buffer:
                            reason = "duplicate"
                        elif offset >= session.recv_window.size:
                            reason = "out_of_window"
                        elif envelope.session_seq <= session.recv_window.base_seq:
                            reason = "stale"
                        else:
                            reason = "unknown"
                        logger.warning(
                            "Dropping message seq=%s type=%s reason=%s base_seq=%s window=%s",
                            envelope.session_seq,
                            envelope.type,
                            reason,
                            session.recv_window.base_seq,
                            session.recv_window.size,
                        )
                        continue
                    for ready_envelope in ready:
                        await _handle_biz_envelope(ready_envelope, session=session)
                else:
                    await _maybe_ack(envelope, websocket, session=session)
                    await _handle_biz_envelope(envelope, session=session)

    except WebSocketDisconnect:
        logger.info("Worker connection closed")
    except Exception:
        logger.exception("Worker control-plane encountered an error; closing connection")
        await websocket.close(code=1011, reason="internal error")
    finally:
        if poll_task:
            poll_task.cancel()
        if session:
            worker_manager.mark_disconnected(session.worker_instance_id, session.worker_name)
            logger.info("Worker %s marked disconnected", session.worker_name)
