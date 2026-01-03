from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

def _now() -> datetime:
    return datetime.now(timezone.utc)

def _key(value: str) -> str:
    return value.lower()

def _generate_id() -> str:
    return str(uuid4())
