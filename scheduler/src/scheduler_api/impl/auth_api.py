from __future__ import annotations

from fastapi import HTTPException, status

from scheduler_api.apis.auth_api_base import BaseAuthApi
from scheduler_api.auth.service import authenticate_user, create_access_token
from scheduler_api.models.auth_login200_response import AuthLogin200Response
from scheduler_api.models.auth_login200_response_user import AuthLogin200ResponseUser
from scheduler_api.models.auth_login_request import AuthLoginRequest
from scheduler_api.models.auth_login401_response import AuthLogin401Response


class AuthApiImpl(BaseAuthApi):
    async def auth_login(
        self,
        auth_login_request: AuthLoginRequest,
    ) -> AuthLogin200Response:
        if auth_login_request is None:
            raise HTTPException(
                status.HTTP_401_UNAUTHORIZED,
                detail=AuthLogin401Response(
                    error="unauthorized",
                    message="Missing credentials",
                ).model_dump(by_alias=True),
            )
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
