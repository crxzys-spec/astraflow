"""Authentication helpers (password hashing and JWT issuance)."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from uuid import uuid4

import bcrypt
import jwt
from fastapi import HTTPException, status
from sqlalchemy import select

from scheduler_api.audit import record_audit_event
from scheduler_api.db.models import RoleRecord, UserRecord, UserRoleRecord
from scheduler_api.db.session import AsyncSessionLocal, SessionLocal


JWT_ALGORITHM = os.getenv("SCHEDULER_JWT_ALGORITHM", "HS256")
JWT_SECRET = os.getenv("SCHEDULER_JWT_SECRET", "dev-secret")
JWT_ACCESS_MINUTES = int(os.getenv("SCHEDULER_JWT_ACCESS_MINUTES", "60"))


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


def _get_user_with_roles(username: str) -> Optional[AuthenticatedUser]:
    with SessionLocal() as session:
        user = session.execute(
            select(UserRecord).where(UserRecord.username == username)
        ).scalar_one_or_none()
        if not user:
            return None
        role_rows = session.execute(
            select(RoleRecord.name)
            .join(UserRoleRecord, UserRoleRecord.role_id == RoleRecord.id)
            .where(UserRoleRecord.user_id == user.id)
        ).scalars()
        roles = list(role_rows)
        return AuthenticatedUser(user, roles)


def _unauthorized(message: str = "Invalid credentials") -> HTTPException:
    return HTTPException(status.HTTP_401_UNAUTHORIZED, detail={"error": "unauthorized", "message": message})


def authenticate_user(username: str, password: str) -> AuthenticatedUser:
    user = _get_user_with_roles(username)
    if not user:
        record_audit_event(
            actor_id=None,
            action="auth.login.failure",
            target_type="user",
            target_id=username,
            metadata={"reason": "user_not_found"},
        )
        raise _unauthorized()
    with SessionLocal() as session:
        db_user = session.get(UserRecord, user.user_id)
    if db_user is None or not db_user.is_active:
        record_audit_event(
            actor_id=None,
            action="auth.login.failure",
            target_type="user",
            target_id=username,
            metadata={"reason": "inactive"},
        )
        raise _unauthorized()
    if not verify_password(password, db_user.password_hash):
        record_audit_event(
            actor_id=None,
            action="auth.login.failure",
            target_type="user",
            target_id=username,
            metadata={"reason": "invalid_password"},
        )
        raise _unauthorized()
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
    async with AsyncSessionLocal() as session:
        user = await session.get(UserRecord, user_id)
        if not user or not user.is_active:
            raise _unauthorized("Invalid token")
        role_rows = await session.execute(
            select(RoleRecord.name)
            .join(UserRoleRecord, UserRoleRecord.role_id == RoleRecord.id)
            .where(UserRoleRecord.user_id == user.id)
        )
        roles = list(role_rows.scalars())
        return AuthenticatedUser(user, roles)
