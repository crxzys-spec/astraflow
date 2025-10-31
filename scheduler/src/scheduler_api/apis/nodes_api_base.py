# coding: utf-8

from typing import ClassVar, Dict, List, Tuple  # noqa: F401

from pydantic import Field, StrictStr, field_validator
from typing import Optional
from typing_extensions import Annotated
from scheduler_api.models.get_node200_response import GetNode200Response
from scheduler_api.models.list_node_categories200_response import ListNodeCategories200Response
from scheduler_api.models.list_nodes200_response import ListNodes200Response
from scheduler_api.models.start_run400_response import StartRun400Response
from scheduler_api.security_api import get_token_bearerAuth

class BaseNodesApi:
    subclasses: ClassVar[Tuple] = ()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        BaseNodesApi.subclasses = BaseNodesApi.subclasses + (cls,)
    async def list_nodes(
        self,
        limit: Optional[Annotated[int, Field(le=200, strict=True, ge=1)]],
        cursor: Optional[StrictStr],
        category: Optional[StrictStr],
        status: Optional[StrictStr],
        tag: Optional[StrictStr],
        q: Optional[StrictStr],
    ) -> ListNodes200Response:
        ...


    async def get_node(
        self,
        nodeId: StrictStr,
    ) -> GetNode200Response:
        ...


    async def list_node_categories(
        self,
    ) -> ListNodeCategories200Response:
        ...
