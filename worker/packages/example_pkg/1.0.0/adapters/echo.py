"""Simple echo handler returning input parameters."""

from __future__ import annotations

from typing import Any, Dict

from worker.agent.runner import ExecutionContext


def _build_payload(context: ExecutionContext) -> Dict[str, Any]:
    message = context.params.get("message", "")
    return {
        "status": "succeeded",
        "outputs": {"echo": message},
    }


class EchoAdapter:
    """Adapter with sync/async entrypoints for testing."""

    async def echo(self, context: ExecutionContext) -> Dict[str, Any]:
        return _build_payload(context)

    async def async_run(self, context: ExecutionContext) -> Dict[str, Any]:
        return _build_payload(context)


async def echo(context: ExecutionContext) -> Dict[str, Any]:
    """Module-level async handler entrypoint."""

    return _build_payload(context)


async def async_run(context: ExecutionContext) -> Dict[str, Any]:
    """Compatibility alias kept for older manifests."""

    return _build_payload(context)
