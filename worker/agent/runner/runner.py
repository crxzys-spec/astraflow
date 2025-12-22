"""Node execution runner leveraging adapter registry."""

from __future__ import annotations

import asyncio
import inspect
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


EXEC_MODE_AUTO = "auto"
EXEC_MODE_INLINE = "inline"
EXEC_MODE_THREAD = "thread"
EXEC_MODE_ALIASES = {
    "async": EXEC_MODE_INLINE,
    "event_loop": EXEC_MODE_INLINE,
    "loop": EXEC_MODE_INLINE,
}


class Runner:
    """Delegates command execution to package handlers."""

    def __init__(self, registry: AdapterRegistry, *, default_exec_mode: str = EXEC_MODE_AUTO) -> None:
        self._registry = registry
        self._default_exec_mode = self._normalize_exec_mode(default_exec_mode) or EXEC_MODE_AUTO

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
        exec_mode = self._resolve_exec_mode(descriptor.metadata)
        LOGGER.debug(
            "Executing handler %s for run=%s task=%s",
            handler_key,
            context.run_id,
            context.task_id,
        )
        if exec_mode == EXEC_MODE_THREAD:
            result = await self._execute_in_thread(handler_callable, context)
        elif exec_mode == EXEC_MODE_INLINE:
            result = await self._execute_inline(handler_callable, context)
        else:
            result = await self._execute_auto(handler_callable, context)
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

    def _resolve_exec_mode(self, metadata: Dict[str, Any]) -> str:
        config = metadata.get("config") if isinstance(metadata, dict) else None
        node_exec_mode = None
        if isinstance(config, dict):
            node_exec_mode = config.get("exec_mode")
        adapter_exec_mode = metadata.get("exec_mode") if isinstance(metadata, dict) else None
        return (
            self._normalize_exec_mode(node_exec_mode)
            or self._normalize_exec_mode(adapter_exec_mode)
            or self._default_exec_mode
        )

    @staticmethod
    def _normalize_exec_mode(value: Any) -> Optional[str]:
        if not isinstance(value, str):
            return None
        normalized = value.strip().lower()
        if normalized in {EXEC_MODE_AUTO, EXEC_MODE_INLINE, EXEC_MODE_THREAD}:
            return normalized
        return EXEC_MODE_ALIASES.get(normalized)

    @staticmethod
    def _select_callable(handler_callable):
        if callable(getattr(handler_callable, "async_run", None)):
            return handler_callable.async_run
        if callable(getattr(handler_callable, "run", None)):
            return handler_callable.run
        return handler_callable

    async def _execute_inline(self, handler_callable, context):
        target = self._select_callable(handler_callable)
        result = target(context)
        return await self._maybe_await(result)

    async def _execute_auto(self, handler_callable, context):
        target = self._select_callable(handler_callable)
        if inspect.iscoroutinefunction(target):
            result = target(context)
            return await self._maybe_await(result)
        result = await asyncio.to_thread(target, context)
        if hasattr(result, "__await__"):
            return await result
        return result

    async def _execute_in_thread(self, handler_callable, context):
        target = self._select_callable(handler_callable)
        if inspect.iscoroutinefunction(target):
            LOGGER.debug("exec_mode=thread requested for async handler; running inline")
            result = target(context)
            return await self._maybe_await(result)
        result = await asyncio.to_thread(target, context)
        if hasattr(result, "__await__"):
            LOGGER.warning("Threaded handler returned awaitable; running inline")
            return await result
        return result

    @staticmethod
    async def _maybe_await(value: Any) -> Any:
        if hasattr(value, "__await__"):
            return await value
        return value
