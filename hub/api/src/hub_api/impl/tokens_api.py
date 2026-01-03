from __future__ import annotations

from hub_api.apis.tokens_api_base import BaseTokensApi
from hub_api.models.access_token import AccessToken
from hub_api.models.access_token_create_request import AccessTokenCreateRequest
from hub_api.models.access_token_list import AccessTokenList
from hub_api.services.tokens_service import TokensService

_service = TokensService()


class TokensApiImpl(BaseTokensApi):
    async def list_tokens(self) -> AccessTokenList:
        return await _service.list_tokens()

    async def create_publish_token(
        self,
        access_token_create_request: AccessTokenCreateRequest,
    ) -> AccessToken:
        return await _service.create_publish_token(access_token_create_request)

    async def revoke_token(
        self,
        tokenId: str,
    ) -> None:
        return await _service.revoke_token(tokenId)
