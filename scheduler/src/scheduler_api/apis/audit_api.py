# coding: utf-8

from typing import Dict, List  # noqa: F401
import importlib
import pkgutil

from scheduler_api.apis.audit_api_base import BaseAuditApi
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
from scheduler_api.models.list_audit_events200_response import ListAuditEvents200Response
from scheduler_api.security_api import get_token_bearerAuth

router = APIRouter()

ns_pkg = scheduler_api.impl
for _, name, _ in pkgutil.iter_modules(ns_pkg.__path__, ns_pkg.__name__ + "."):
    importlib.import_module(name)


@router.get(
    "/api/v1/audit-events",
    responses={
        200: {"model": ListAuditEvents200Response, "description": "OK"},
    },
    tags=["Audit"],
    summary="List audit events",
    response_model_by_alias=True,
)
async def list_audit_events(
    limit: Optional[Annotated[int, Field(le=200, ge=1)]] = Query(50, description="", alias="limit", ge=1, le=200),
    cursor: Annotated[Optional[StrictStr], Field(description="Reserved for future pagination")] = Query(None, description="Reserved for future pagination", alias="cursor"),
    action: Annotated[Optional[StrictStr], Field(description="Filter by action name")] = Query(None, description="Filter by action name", alias="action"),
    actor_id: Annotated[Optional[StrictStr], Field(description="Filter by actor id")] = Query(None, description="Filter by actor id", alias="actorId"),
    target_type: Annotated[Optional[StrictStr], Field(description="Filter by target type")] = Query(None, description="Filter by target type", alias="targetType"),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth
    ),
) -> ListAuditEvents200Response:
    if not BaseAuditApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseAuditApi.subclasses[0]().list_audit_events(limit, cursor, action, actor_id, target_type)
