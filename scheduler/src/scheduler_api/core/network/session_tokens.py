"""Stateless session token issuance/validation for worker control-plane."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any, Dict, Optional, Tuple

from scheduler_api.config.settings import get_settings


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def issue_session_token(
    *,
    session_id: str,
    worker_instance_id: str,
    tenant: str,
    ttl_seconds: Optional[int] = None,
) -> Tuple[str, int]:
    settings = get_settings()
    ttl = int(ttl_seconds if ttl_seconds is not None else settings.session_token_ttl_seconds)
    now = int(time.time())
    payload = {
        "sid": session_id,
        "wid": worker_instance_id,
        "tenant": tenant,
        "iat": now,
        "exp": now + ttl,
    }
    payload_bytes = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    sig = hmac.new(settings.session_secret.encode("utf-8"), payload_bytes, hashlib.sha256).digest()
    token = f"{_b64encode(payload_bytes)}.{_b64encode(sig)}"
    return token, payload["exp"]


def validate_session_token(
    token: str,
    *,
    session_id: str,
    worker_instance_id: str,
    tenant: str,
) -> Optional[Dict[str, Any]]:
    settings = get_settings()
    try:
        payload_b64, sig_b64 = token.split(".", 1)
        payload_bytes = _b64decode(payload_b64)
        sig = _b64decode(sig_b64)
    except Exception:
        return None

    expected_sig = hmac.new(settings.session_secret.encode("utf-8"), payload_bytes, hashlib.sha256).digest()
    if not hmac.compare_digest(sig, expected_sig):
        return None

    try:
        payload = json.loads(payload_bytes.decode("utf-8"))
    except json.JSONDecodeError:
        return None

    now = int(time.time())
    if payload.get("sid") != session_id:
        return None
    if payload.get("wid") != worker_instance_id:
        return None
    if payload.get("tenant") != tenant:
        return None
    exp = payload.get("exp")
    if exp is None or not isinstance(exp, int) or exp < now:
        return None
    return payload
