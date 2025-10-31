"""Simple echo handler returning input parameters."""

from __future__ import annotations

from typing import Any, Dict

from worker.agent.runner import ExecutionContext


class EchoAdapter:
    """Adapter with sync/async entrypoints for testing."""

    async def async_run(self, context: ExecutionContext) -> Dict[str, Any]:
        message = context.params.get("message", "")
        return {
            "status": "succeeded",
            "outputs": {"echo": message},
        }


async def async_run(context: ExecutionContext) -> Dict[str, Any]:
    """Module-level async handler entrypoint."""

    message = context.params.get("message", "")
    return {
        "status": "succeeded",
        "outputs": {"echo": message},
    }
