from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select

from hub_api.db.models import HubUser
from hub_api.db.security import hash_password, verify_password
from hub_api.db.session import SessionLocal
from hub_api.repo.accounts import get_account
from hub_api.repo.tokens import create_token
from hub_api.models.auth_login_request import AuthLoginRequest
from hub_api.models.auth_register_request import AuthRegisterRequest
from hub_api.models.auth_response import AuthResponse

DEFAULT_AUTH_SCOPES = ["read", "publish"]


def _normalize_username(username: str) -> str:
    return username.strip()


def _create_auth_response(user_id: str, token_label: str) -> AuthResponse:
    token = create_token(
        owner_id=user_id,
        label=token_label,
        scopes=DEFAULT_AUTH_SCOPES,
        package_name=None,
        expires_at=None,
    )
    account = get_account(user_id)
    return AuthResponse.from_dict({"account": account, "token": token})


class AuthService:
    async def register_account(
        self,
        auth_register_request: AuthRegisterRequest,
    ) -> AuthResponse:
        if auth_register_request is None:
            raise HTTPException(status_code=400, detail="Payload is required.")
        username = _normalize_username(auth_register_request.username or "")
        password_value = auth_register_request.password
        password = (
            password_value.get_secret_value()
            if hasattr(password_value, "get_secret_value")
            else str(password_value or "")
        )
        if not username or not password:
            raise HTTPException(status_code=400, detail="Username and password are required.")

        with SessionLocal() as session:
            existing = session.get(HubUser, username)
            if existing is None:
                existing = session.execute(
                    select(HubUser).where(HubUser.username == username)
                ).scalar_one_or_none()
            if existing is not None:
                raise HTTPException(status_code=409, detail="Username already exists.")

            user = HubUser(
                id=username,
                username=username,
                display_name=auth_register_request.display_name,
                email=auth_register_request.email,
                password_hash=hash_password(password),
            )
            session.add(user)
            session.commit()

        return _create_auth_response(username, "register")

    async def login_account(
        self,
        auth_login_request: AuthLoginRequest,
    ) -> AuthResponse:
        if auth_login_request is None:
            raise HTTPException(status_code=400, detail="Payload is required.")
        username = _normalize_username(auth_login_request.username or "")
        password_value = auth_login_request.password
        password = (
            password_value.get_secret_value()
            if hasattr(password_value, "get_secret_value")
            else str(password_value or "")
        )
        if not username or not password:
            raise HTTPException(status_code=400, detail="Username and password are required.")

        with SessionLocal() as session:
            user = session.get(HubUser, username)
            if user is None:
                user = session.execute(
                    select(HubUser).where(HubUser.username == username)
                ).scalar_one_or_none()
            if user is None or not verify_password(password, user.password_hash):
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

        return _create_auth_response(username, "login")
