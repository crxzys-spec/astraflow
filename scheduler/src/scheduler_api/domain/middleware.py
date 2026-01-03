"""Middleware helpers for the run registry."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID


def extract_middleware_entries(raw: Optional[Any]) -> Tuple[List[str], List[Dict[str, Any]]]:
    ids: List[str] = []
    defs: List[Dict[str, Any]] = []
    if not raw:
        return ids, defs
    if not isinstance(raw, list):
        return ids, defs
    for entry in raw:
        if entry is None:
            continue
        if isinstance(entry, dict):
            mw_id = entry.get("id") or entry.get("node_id") or entry.get("nodeId")
            if isinstance(mw_id, (UUID, str)) and mw_id:
                ids.append(str(mw_id))
            defs.append(entry)
            continue
        # Pydantic models / objects with id attributes
        candidate_id = getattr(entry, "id", None) or getattr(entry, "node_id", None) or getattr(entry, "nodeId", None)
        if candidate_id:
            mw_id = str(candidate_id)
            ids.append(mw_id)
            if hasattr(entry, "model_dump"):
                try:
                    defs.append(entry.model_dump(by_alias=True, exclude_none=True))
                except Exception:
                    defs.append({"id": mw_id})
            else:
                defs.append({"id": mw_id})
            continue
        mw_id = str(entry)
        if mw_id:
            ids.append(mw_id)
            defs.append({"id": mw_id})
    return ids, defs
