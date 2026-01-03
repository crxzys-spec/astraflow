from __future__ import annotations

from typing import Any

from sqlalchemy import select

from hub_api.db.models import HubUser
from hub_api.db.session import SessionLocal
from hub_api.repo.state import _USERS

def _account_from_model(user: HubUser) -> dict[str, Any]:
    return {
        "id": user.id,
        "username": user.username,
        "displayName": user.display_name,
        "email": user.email,
    }

def get_account(user_id: str) -> dict[str, Any] | None:
    with SessionLocal() as session:
        record = session.get(HubUser, user_id)
        if record is None:
            record = session.execute(
                select(HubUser).where(HubUser.username == user_id)
            ).scalar_one_or_none()
        if record is not None:
            return _account_from_model(record)
    return _USERS.get(user_id)
