# coding: utf-8

from typing import Dict, List  # noqa: F401
import importlib
import pkgutil

from scheduler_api.apis.nodes_api_base import BaseNodesApi
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
from pydantic import Field, StrictStr, field_validator
from typing import Optional
from typing_extensions import Annotated
from scheduler_api.models.get_node200_response import GetNode200Response
from scheduler_api.models.list_node_categories200_response import ListNodeCategories200Response
from scheduler_api.models.list_nodes200_response import ListNodes200Response
from scheduler_api.models.start_run400_response import StartRun400Response
from scheduler_api.security_api import get_token_bearerAuth

router = APIRouter()

ns_pkg = scheduler_api.impl
for _, name, _ in pkgutil.iter_modules(ns_pkg.__path__, ns_pkg.__name__ + "."):
    importlib.import_module(name)


@router.get(
    "/api/v1/nodes",
    responses={
        200: {"model": ListNodes200Response, "description": "OK"},
    },
    tags=["Nodes"],
    summary="List available nodes (catalog)",
    response_model_by_alias=True,
)
async def list_nodes(
    limit: Optional[Annotated[int, Field(le=200, strict=True, ge=1)]] = Query(50, description="", alias="limit", ge=1, le=200),
    cursor: Optional[StrictStr] = Query(None, description="", alias="cursor"),
    category: Optional[StrictStr] = Query(None, description="", alias="category"),
    status: Optional[StrictStr] = Query(None, description="", alias="status"),
    tag: Optional[StrictStr] = Query(None, description="", alias="tag"),
    q: Optional[StrictStr] = Query(None, description="", alias="q"),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth
    ),
) -> ListNodes200Response:
    if not BaseNodesApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseNodesApi.subclasses[0]().list_nodes(limit, cursor, category, status, tag, q)


@router.get(
    "/api/v1/nodes/{nodeId}",
    responses={
        200: {"model": GetNode200Response, "description": "OK"},
        404: {"model": StartRun400Response, "description": "Resource not found"},
    },
    tags=["Nodes"],
    summary="Get a node definition",
    response_model_by_alias=True,
)
async def get_node(
    nodeId: StrictStr = Path(..., description=""),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth
    ),
) -> GetNode200Response:
    if not BaseNodesApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseNodesApi.subclasses[0]().get_node(nodeId)


@router.get(
    "/api/v1/nodes:categories",
    responses={
        200: {"model": ListNodeCategories200Response, "description": "OK"},
    },
    tags=["Nodes"],
    summary="List node categories",
    response_model_by_alias=True,
)
async def list_node_categories(
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth
    ),
) -> ListNodeCategories200Response:
    if not BaseNodesApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseNodesApi.subclasses[0]().list_node_categories()
