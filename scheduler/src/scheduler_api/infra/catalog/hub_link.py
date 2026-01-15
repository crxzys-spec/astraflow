"""Helpers for storing Hub metadata alongside local packages."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

HUB_LINK_FILENAME = ".hub.json"
HUB_LINK_KEYS = {
    "hubName",
    "hubVersion",
    "ownerId",
    "ownerName",
    "visibility",
    "publishedAt",
    "archiveSha256",
}


def read_hub_link(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    sanitized = {key: value for key, value in payload.items() if key in HUB_LINK_KEYS}
    if not sanitized:
        return None
    return sanitized


def write_hub_link(target_dir: Path, payload: dict[str, Any]) -> Path:
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / HUB_LINK_FILENAME
    sanitized = {key: value for key, value in payload.items() if key in HUB_LINK_KEYS}
    text = json.dumps(sanitized, ensure_ascii=True, sort_keys=True)
    path.write_text(text, encoding="utf-8")
    return path
