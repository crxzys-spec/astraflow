# coding: utf-8

from typing import Dict, List  # noqa: F401
import importlib
import pkgutil

from hub_api.apis.audit_api_base import BaseAuditApi
import hub_api.impl

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

from hub_api.models.extra_models import TokenModel  # noqa: F401
from pydantic import Field, StrictStr
from typing import Optional
from typing_extensions import Annotated
from hub_api.models.audit_event_list import AuditEventList
from hub_api.models.error import Error
from hub_api.security_api import get_token_bearerAuth

router = APIRouter()

ns_pkg = hub_api.impl
for _, name, _ in pkgutil.iter_modules(ns_pkg.__path__, ns_pkg.__name__ + "."):
    importlib.import_module(name)


@router.get(
    "/api/v1/audit",
    responses={
        200: {"model": AuditEventList, "description": "OK"},
        401: {"model": Error, "description": "Unauthorized"},
    },
    tags=["Audit"],
    summary="List audit events",
    response_model_by_alias=True,
)
async def list_audit_events(
    actor: Annotated[Optional[StrictStr], Field(description="Filter by actor id")] = Query(None, description="Filter by actor id", alias="actor"),
    action: Annotated[Optional[StrictStr], Field(description="Filter by action")] = Query(None, description="Filter by action", alias="action"),
    limit: Annotated[Optional[Annotated[int, Field(le=200, ge=1)]], Field(description="Max events to return")] = Query(50, description="Max events to return", alias="limit", ge=1, le=200),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth, scopes=["read"]
    ),
) -> AuditEventList:
    if not BaseAuditApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseAuditApi.subclasses[0]().list_audit_events(actor, action, limit)
