from __future__ import annotations

from hub_api.apis.auth_api_base import BaseAuthApi
from hub_api.models.auth_login_request import AuthLoginRequest
from hub_api.models.auth_register_request import AuthRegisterRequest
from hub_api.models.auth_response import AuthResponse
from hub_api.services.auth_service import AuthService

_service = AuthService()


class AuthApiImpl(BaseAuthApi):
    async def register_account(
        self,
        auth_register_request: AuthRegisterRequest,
    ) -> AuthResponse:
        return await _service.register_account(auth_register_request)

    async def login_account(
        self,
        auth_login_request: AuthLoginRequest,
    ) -> AuthResponse:
        return await _service.login_account(auth_login_request)
