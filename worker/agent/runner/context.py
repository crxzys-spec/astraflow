"""Execution context passed to handlers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from shared.models.ws.cmd.dispatch import ResourceRef
    from ..resource_registry import ResourceRegistry, ResourceHandle
    from ..feedback import FeedbackPublisher


@dataclass
class ExecutionContext:
    run_id: str
    task_id: str
    node_id: str
    package_name: str
    package_version: str
    params: Dict[str, Any]
    data_dir: Path
    tenant: str
    host_node_id: Optional[str] = None
    middleware_chain: Optional[List[str]] = None
    chain_index: Optional[int] = None
    trace: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    resource_refs: Optional[List["ResourceRef"]] = None
    resource_registry: Optional["ResourceRegistry"] = None
    leased_resources: Optional[Dict[str, "ResourceHandle"]] = None
    feedback: Optional["FeedbackPublisher"] = None
    next_handler: Optional[
        Callable[
            [
                "ExecutionContext",
                Optional[Dict[str, Any]],
                Optional[Dict[str, Any]],
                Optional[Dict[str, Any]],
                Optional[int],
            ],
            Awaitable[Dict[str, Any]],
        ]
    ] = None

    async def next(
        self,
        payload: Optional[Dict[str, Any]] = None,
        *,
        host_ctx: Optional[Dict[str, Any]] = None,
        middleware_ctx: Optional[Dict[str, Any]] = None,
        timeout_ms: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Call the next middleware/host in the chain via scheduler."""

        if not self.next_handler:
            raise RuntimeError("middleware next is not available in this context")
        return await self.next_handler(self, payload, host_ctx, middleware_ctx, timeout_ms)
