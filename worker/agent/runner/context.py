"""Execution context passed to handlers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from shared.models.ws.cmd.dispatch import ResourceRef
    from ..resource_registry import ResourceRegistry, ResourceHandle


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
    trace: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    resource_refs: Optional[List["ResourceRef"]] = None
    resource_registry: Optional["ResourceRegistry"] = None
    leased_resources: Optional[Dict[str, "ResourceHandle"]] = None
