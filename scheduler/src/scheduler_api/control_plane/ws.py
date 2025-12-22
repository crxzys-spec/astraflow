"""WebSocket entrypoint for the scheduler control-plane."""

from __future__ import annotations

from fastapi import APIRouter, WebSocket

from scheduler_api.control_plane.biz.adapters.handlers import register_handlers
from scheduler_api.control_plane.network import ControlPlaneServer

router = APIRouter()
_server = ControlPlaneServer()
register_handlers(_server)


@router.websocket("/ws/worker")
async def worker_control_endpoint(websocket: WebSocket) -> None:
    await _server.handle_websocket(websocket)
