"""Authentication helpers (password hashing and JWT issuance)."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from uuid import uuid4

import bcrypt
import jwt

from scheduler_api.http.errors import unauthorized

from scheduler_api.audit import record_audit_event
from scheduler_api.db.models import UserRecord
from scheduler_api.db.session import run_in_session
from scheduler_api.repo.users import AsyncUserRepository, UserRepository


JWT_ALGORITHM = os.getenv("SCHEDULER_JWT_ALGORITHM", "HS256")
JWT_SECRET = os.getenv("SCHEDULER_JWT_SECRET", "dev-secret")
# Default access token lifetime: 1 year (365 days).
JWT_ACCESS_MINUTES = int(os.getenv("SCHEDULER_JWT_ACCESS_MINUTES", str(60 * 24 * 365)))


class AuthenticatedUser:
    def __init__(self, user: UserRecord, roles: List[str]):
        self.user_id = user.id
        self.username = user.username
        self.display_name = user.display_name
        self.roles = roles
        self.is_active = user.is_active


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


_user_repo = UserRepository()
_async_user_repo = AsyncUserRepository()


def _get_user_with_roles(username: str) -> Optional[tuple[UserRecord, list[str]]]:
    def _fetch(session) -> Optional[tuple[UserRecord, list[str]]]:
        user = _user_repo.get_by_username(username, session=session)
        if not user:
            return None
        roles = _user_repo.list_role_names(user.id, session=session)
        return user, roles

    return run_in_session(_fetch)


def _unauthorized(message: str = "Invalid credentials"):
    return unauthorized(message)


def authenticate_user(username: str, password: str) -> AuthenticatedUser:
    result = _get_user_with_roles(username)
    if not result:
        record_audit_event(
            actor_id=None,
            action="auth.login.failure",
            target_type="user",
            target_id=username,
            metadata={"reason": "user_not_found"},
        )
        raise _unauthorized()
    user_record, roles = result
    if not user_record.is_active:
        record_audit_event(
            actor_id=None,
            action="auth.login.failure",
            target_type="user",
            target_id=username,
            metadata={"reason": "inactive"},
        )
        raise _unauthorized()
    if not verify_password(password, user_record.password_hash):
        record_audit_event(
            actor_id=None,
            action="auth.login.failure",
            target_type="user",
            target_id=username,
            metadata={"reason": "invalid_password"},
        )
        raise _unauthorized()
    user = AuthenticatedUser(user_record, roles)
    record_audit_event(
        actor_id=user.user_id,
        action="auth.login.success",
        target_type="user",
        target_id=user.user_id,
        metadata={"username": username},
    )
    return user


def create_access_token(user: AuthenticatedUser) -> tuple[str, int]:
    expires_delta = timedelta(minutes=JWT_ACCESS_MINUTES)
    expire_ts = datetime.now(timezone.utc) + expires_delta
    payload = {
        "sub": user.user_id,
        "username": user.username,
        "displayName": user.display_name,
        "roles": user.roles,
        "exp": expire_ts,
        "jti": str(uuid4()),
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token, int(expires_delta.total_seconds())


async def decode_access_token(token: str) -> AuthenticatedUser:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError as exc:  # type: ignore[attr-defined]
        raise _unauthorized("Invalid token") from exc
    user_id = payload.get("sub")
    if not user_id:
        raise _unauthorized("Invalid token")
    result = await _async_user_repo.get_with_roles_by_id(user_id)
    if not result:
        raise _unauthorized("Invalid token")
    user, roles = result
    if not user.is_active:
        raise _unauthorized("Invalid token")
    return AuthenticatedUser(user, roles)
