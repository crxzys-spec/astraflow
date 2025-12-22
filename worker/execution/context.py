"""Execution context definitions for dispatched nodes."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional, Protocol, TYPE_CHECKING

from shared.models.biz.exec.dispatch import ExecDispatchPayload

from worker.execution.runtime import FeedbackPublisher, ResourceRegistry
from worker.handlers.next_handler import NextHandler
from worker.config import WorkerSettings

if TYPE_CHECKING:
    from shared.models.biz.exec.dispatch import ResourceRef
    from worker.execution.runtime import ResourceHandle


class FeedbackSender(Protocol):
    async def send_feedback(self, payload: Any, *, corr: Optional[str] = None, seq: Optional[int] = None) -> None: ...


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
    resource_registry: Optional[ResourceRegistry] = None
    leased_resources: Optional[Dict[str, "ResourceHandle"]] = None
    feedback: Optional[FeedbackPublisher] = None
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


@dataclass
class ExecutionContextFactory:
    settings: WorkerSettings
    next_handler: NextHandler
    resource_registry: Optional[ResourceRegistry] = None

    def build(self, dispatch: ExecDispatchPayload, *, feedback_sender: FeedbackSender) -> ExecutionContext:
        run_id = dispatch.run_id
        task_id = dispatch.task_id
        parameters = dispatch.parameters or {}
        safe_task_id = self._sanitize_path_segment(task_id)
        data_dir = Path(self.settings.data_dir) / run_id / safe_task_id
        data_dir.mkdir(parents=True, exist_ok=True)
        metadata = self._build_metadata(dispatch)
        resource_refs = list(dispatch.resource_refs) if dispatch.resource_refs else None
        if resource_refs:
            metadata["resource_refs"] = [ref.model_dump(exclude_none=True) for ref in resource_refs]
        if dispatch.affinity:
            metadata["affinity"] = dispatch.affinity.model_dump(exclude_none=True)
        context = ExecutionContext(
            run_id=run_id,
            task_id=task_id,
            node_id=dispatch.node_id,
            package_name=dispatch.package_name,
            package_version=dispatch.package_version,
            params=parameters,
            data_dir=data_dir,
            tenant=self.settings.tenant,
            host_node_id=dispatch.host_node_id,
            middleware_chain=dispatch.middleware_chain,
            chain_index=dispatch.chain_index,
            trace=None,
            metadata=metadata,
            resource_refs=resource_refs,
            resource_registry=self.resource_registry,
            feedback=FeedbackPublisher(feedback_sender, run_id=run_id, task_id=task_id),
        )
        context.next_handler = self.next_handler.middleware_next
        return context

    def _build_metadata(self, dispatch: ExecDispatchPayload) -> dict[str, Any]:
        metadata = {
            "concurrency_key": dispatch.concurrency_key,
            "constraints": dispatch.constraints.model_dump(exclude_none=True),
        }
        if dispatch.host_node_id:
            metadata["host_node_id"] = dispatch.host_node_id
        if dispatch.middleware_chain:
            metadata["middleware_chain"] = list(dispatch.middleware_chain)
        if dispatch.chain_index is not None:
            metadata["chain_index"] = dispatch.chain_index
        return metadata

    @staticmethod
    def _sanitize_path_segment(segment: str) -> str:
        cleaned = re.sub(r'[<>:"/\\\\|?*]', "_", segment)
        cleaned = cleaned.strip(". ")
        return cleaned or "task"
