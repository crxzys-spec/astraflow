# coding: utf-8

from typing import Dict, List  # noqa: F401
import importlib
import pkgutil

from scheduler_api.apis.events_api_base import BaseEventsApi
import scheduler_api.impl

from fastapi import (  # noqa: F401
    APIRouter,
    Body,
    Cookie,
    Depends,
    Form,
    Header,
    HTTPException,
    Path,
    Query,
    Response,
    Security,
    status,
)

from scheduler_api.models.extra_models import TokenModel  # noqa: F401
from pydantic import Field, StrictStr
from typing import Optional
from typing_extensions import Annotated
from scheduler_api.security_api import get_token_bearerAuth

router = APIRouter()

ns_pkg = scheduler_api.impl
for _, name, _ in pkgutil.iter_modules(ns_pkg.__path__, ns_pkg.__name__ + "."):
    importlib.import_module(name)


@router.get(
    "/api/v1/events",
    responses={
        200: {"model": str, "description": "text/event-stream"},
    },
    tags=["Events"],
    summary="Global Server-Sent Events stream (firehose; no query parameters)",
    response_model_by_alias=True,
)
async def sse_global_events(
    client_session_id: Annotated[StrictStr, Field(description="Frontend-generated session identifier (UUID) used to route SSE events.")] = Query(None, description="Frontend-generated session identifier (UUID) used to route SSE events.", alias="clientSessionId"),
    last_event_id: Annotated[Optional[StrictStr], Field(description="Resume SSE from a specific monotonic event id")] = Header(None, description="Resume SSE from a specific monotonic event id"),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth
    ),
) -> str:
    if not BaseEventsApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseEventsApi.subclasses[0]().sse_global_events(client_session_id, last_event_id)
