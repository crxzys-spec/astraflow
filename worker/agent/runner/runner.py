"""Node execution runner leveraging adapter registry."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..packages import AdapterRegistry
from .context import ExecutionContext

LOGGER = logging.getLogger(__name__)


@dataclass
class NodeExecutionResult:
    status: str
    outputs: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    artifacts: Optional[List[Dict[str, Any]]] = None


class Runner:
    """Delegates command execution to package handlers."""

    def __init__(self, registry: AdapterRegistry) -> None:
        self._registry = registry

    async def execute(
        self,
        context: ExecutionContext,
        handler_key: str,
        *,
        corr: Optional[str] = None,
        seq: Optional[int] = None,
    ) -> NodeExecutionResult:
        descriptor = self._registry.resolve(context.package_name, context.package_version, handler_key)
        handler_callable = descriptor.callable
        LOGGER.debug(
            "Executing handler %s for run=%s task=%s",
            handler_key,
            context.run_id,
            context.task_id,
        )
        if callable(getattr(handler_callable, "async_run", None)):
            result = await handler_callable.async_run(context)
        elif callable(getattr(handler_callable, "run", None)):
            result = await self._maybe_await(handler_callable.run(context))
        else:
            result = await self._maybe_await(handler_callable(context))
        if not isinstance(result, dict):
            raise TypeError("Handler must return a dict containing 'status' and 'outputs'")
        status = result.get("status", "succeeded").upper()
        artifacts = result.get("artifacts")
        metadata = result.get("metadata", {})
        outputs = result.get("outputs")
        if outputs is None:
            outputs = {
                key: value
                for key, value in result.items()
                if key not in {"status", "metadata", "artifacts"}
            }
        return NodeExecutionResult(
            status=status,
            outputs=outputs,
            metadata=metadata,
            artifacts=artifacts if isinstance(artifacts, list) else None,
        )

    @staticmethod
    async def _maybe_await(value: Any) -> Any:
        if hasattr(value, "__await__"):
            return await value
        return value
