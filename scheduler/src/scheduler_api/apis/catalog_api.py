# coding: utf-8

from typing import Dict, List  # noqa: F401
import importlib
import pkgutil

from scheduler_api.apis.catalog_api_base import BaseCatalogApi
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
from scheduler_api.models.catalog_node_search_response import CatalogNodeSearchResponse
from scheduler_api.models.error import Error
from scheduler_api.security_api import get_token_bearerAuth

router = APIRouter()

ns_pkg = scheduler_api.impl
for _, name, _ in pkgutil.iter_modules(ns_pkg.__path__, ns_pkg.__name__ + "."):
    importlib.import_module(name)


@router.get(
    "/api/v1/catalog/nodes/search",
    responses={
        200: {"model": CatalogNodeSearchResponse, "description": "OK"},
        400: {"model": Error, "description": "Invalid input"},
    },
    tags=["Catalog"],
    summary="Search catalog nodes (system + worker capabilities)",
    response_model_by_alias=True,
)
async def search_catalog_nodes(
    q: Annotated[StrictStr, Field(description="Search text applied to node name, type, description, and tags.")] = Query(None, description="Search text applied to node name, type, description, and tags.", alias="q"),
    package: Annotated[Optional[StrictStr], Field(description="Optional package filter derived from search results.")] = Query(None, description="Optional package filter derived from search results.", alias="package"),
    token_bearerAuth: TokenModel = Security(
        get_token_bearerAuth
    ),
) -> CatalogNodeSearchResponse:
    if not BaseCatalogApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseCatalogApi.subclasses[0]().search_catalog_nodes(q, package)
