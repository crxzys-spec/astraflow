from __future__ import annotations

from typing import Any

_USERS: dict[str, dict[str, Any]] = {}
_TOKENS: dict[str, dict[str, Any]] = {}
_TOKEN_BY_SECRET: dict[str, str] = {}
