# coding: utf-8

from typing import ClassVar, Dict, List, Tuple, Any  # noqa: F401

from pydantic import StrictStr
from typing import Any
from hub_api.models.access_token import AccessToken
from hub_api.models.access_token_create_request import AccessTokenCreateRequest
from hub_api.models.access_token_list import AccessTokenList
from hub_api.models.error import Error
from hub_api.security_api import get_token_bearerAuth

class BaseTokensApi:
    subclasses: ClassVar[Tuple] = ()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        BaseTokensApi.subclasses = BaseTokensApi.subclasses + (cls,)
    async def list_tokens(
        self,
    ) -> AccessTokenList:
        ...


    async def create_publish_token(
        self,
        access_token_create_request: AccessTokenCreateRequest,
    ) -> AccessToken:
        ...


    async def revoke_token(
        self,
        tokenId: StrictStr,
    ) -> None:
        ...
