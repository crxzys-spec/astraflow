from __future__ import annotations

from scheduler_api.http.errors import unauthorized

from scheduler_api.apis.auth_api_base import BaseAuthApi
from scheduler_api.auth.service import authenticate_user, create_access_token
from scheduler_api.models.auth_login200_response import AuthLogin200Response
from scheduler_api.models.auth_login200_response_user import AuthLogin200ResponseUser
from scheduler_api.models.auth_login_request import AuthLoginRequest


class AuthApiImpl(BaseAuthApi):
    async def auth_login(
        self,
        auth_login_request: AuthLoginRequest,
    ) -> AuthLogin200Response:
        if auth_login_request is None:
            raise unauthorized("Missing credentials")
        user = authenticate_user(
            auth_login_request.username,
            auth_login_request.password.get_secret_value(),
        )
        token, expires_in = create_access_token(user)
        return AuthLogin200Response(
            accessToken=token,
            tokenType="Bearer",
            expiresIn=expires_in,
            user=AuthLogin200ResponseUser(
                userId=user.user_id,
                username=user.username,
                displayName=user.display_name,
                roles=user.roles,
                isActive=user.is_active,
            ),
        )
