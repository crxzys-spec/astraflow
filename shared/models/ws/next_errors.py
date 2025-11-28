"""Shared middleware.next error codes for scheduler/worker/frontends."""

NEXT_ERROR_CODES = [
    "next_run_finalised",
    "next_duplicate",
    "next_no_chain",
    "next_invalid_chain",
    "next_target_not_ready",
    "next_timeout",
    "next_cancelled",
    "next_unavailable",
]

__all__ = ["NEXT_ERROR_CODES"]
