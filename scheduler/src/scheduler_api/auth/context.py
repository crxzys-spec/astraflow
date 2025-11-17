from __future__ import annotations

from contextvars import ContextVar
from typing import Optional

from scheduler_api.models.extra_models import TokenModel

_current_token: ContextVar[Optional[TokenModel]] = ContextVar("current_token", default=None)


def set_current_token(token: TokenModel) -> None:
    _current_token.set(token)


def get_current_token() -> Optional[TokenModel]:
    return _current_token.get()
