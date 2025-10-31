from __future__ import annotations

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
from shared.models.ws.result import ResultPayload
from shared.models.ws.handshake import HandshakePayload
from shared.models.ws.heartbeat import HeartbeatPayload
from shared.models.ws.register import RegisterPayload

from .manager import WorkerSession, worker_manager
from .run_registry import run_registry
from .orchestrator import run_orchestrator

logger = logging.getLogger(__name__)

router = APIRouter()


def _dump_envelope(envelope: WsEnvelope) -> str:
    payload = envelope.model_dump(by_alias=True, exclude_none=True)
    return json.dumps(jsonable_encoder(payload))


async def _maybe_ack(envelope: WsEnvelope, websocket: WebSocket, *, force: bool = False) -> None:
    if not force and not (envelope.ack and envelope.ack.request):
        return
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


@router.websocket("/ws/worker")
async def worker_control_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    session: Optional[WorkerSession] = None
    logger.info("Worker connection opened from %s", websocket.client)
    try:
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
                record, ready = await run_registry.record_result(result.run_id, result)
                if ready:
                    await run_orchestrator.enqueue(ready)
                artifacts_count = len(record.artifacts) if record else 0
                logger.info(
                    "Result received corr=%s status=%s run=%s artifacts=%s",
                    envelope.corr,
                    result.status.value,
                    result.run_id,
                    artifacts_count,
                )
                await _maybe_ack(envelope, websocket)

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
        if session:
            worker_manager.remove_session(session.worker_id)
            logger.info("Worker %s removed from session registry", session.worker_id)
