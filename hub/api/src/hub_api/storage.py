"""Storage helpers for Hub artifacts."""

from __future__ import annotations

import os
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[5]
DEFAULT_STORAGE_ROOT = PROJECT_ROOT / "var" / "hub" / "storage"

_SAFE_PATTERN = re.compile(r"[^A-Za-z0-9._-]+")


def _safe_component(value: str) -> str:
    cleaned = _SAFE_PATTERN.sub("_", value.strip())
    cleaned = cleaned.strip("._-")
    return cleaned or "artifact"


def get_storage_root() -> Path:
    raw_root = os.getenv("ASTRAFLOW_HUB_STORAGE_ROOT") or os.getenv("HUB_STORAGE_ROOT")
    root = Path(raw_root) if raw_root else DEFAULT_STORAGE_ROOT
    root = root.expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def package_archive_relative_path(name: str, version: str) -> str:
    safe_name = _safe_component(name)
    safe_version = _safe_component(version)
    return str(Path("packages") / safe_name / safe_version / f"{safe_name}-{safe_version}.zip")


def get_package_archive_path(name: str, version: str) -> Path:
    relative = package_archive_relative_path(name, version)
    path = get_storage_root() / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def resolve_storage_path(path_value: str) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        return path
    return get_storage_root() / path_value

