# coding: utf-8

from typing import ClassVar, Dict, List, Tuple  # noqa: F401

from pydantic import Field, StrictStr
from typing import Optional
from typing_extensions import Annotated
from scheduler_api.models.catalog_node_search_response import CatalogNodeSearchResponse
from scheduler_api.models.error import Error
from scheduler_api.security_api import get_token_bearerAuth

class BaseCatalogApi:
    subclasses: ClassVar[Tuple] = ()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        BaseCatalogApi.subclasses = BaseCatalogApi.subclasses + (cls,)
    async def search_catalog_nodes(
        self,
        q: Annotated[StrictStr, Field(description="Search text applied to node name, type, description, and tags.")],
        package: Annotated[Optional[StrictStr], Field(description="Optional package filter derived from search results.")],
    ) -> CatalogNodeSearchResponse:
        ...
