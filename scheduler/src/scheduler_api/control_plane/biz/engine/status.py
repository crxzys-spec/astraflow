"""Status helpers for the scheduler control plane."""

from __future__ import annotations

from typing import Dict

NEXT_ERROR_MESSAGES: Dict[str, str] = {
    "next_run_finalised": "run already in final status",
    "next_duplicate": "duplicate next request",
    "next_no_chain": "middleware chain not found",
    "next_invalid_chain": "invalid chain index",
    "next_target_not_ready": "target node not ready",
    "next_timeout": "next request timed out",
    "next_cancelled": "next request cancelled",
    "next_unavailable": "next request rejected",
}


def normalise_status(value: str) -> str:
    mapping = {
        "succeeded": "succeeded",
        "failed": "failed",
        "skipped": "skipped",
        "cancelled": "cancelled",
        "queued": "queued",
        "running": "running",
    }
    return mapping.get(value.lower(), value.lower())


def get_next_error_message(code: str) -> str:
    return NEXT_ERROR_MESSAGES.get(code, "next request rejected")
