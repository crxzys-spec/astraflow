"""WebSocket entrypoint for the scheduler control-plane."""

from __future__ import annotations

from fastapi import APIRouter, WebSocket

from scheduler_api.core.facade import core_facade

router = APIRouter()
_server = core_facade.build_server()


@router.websocket("/ws/worker")
async def worker_control_endpoint(websocket: WebSocket) -> None:
    await _server.handle_websocket(websocket)
