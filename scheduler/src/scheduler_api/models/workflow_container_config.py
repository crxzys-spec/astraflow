# coding: utf-8

"""
    Scheduler Public API (v1)
"""

from __future__ import annotations

import json
from typing import Any, ClassVar, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field, StrictStr

from scheduler_api.models.workflow_container_loop_policy import WorkflowContainerLoopPolicy
from scheduler_api.models.workflow_container_retry_policy import WorkflowContainerRetryPolicy

try:
    from typing import Self
except ImportError:
    from typing_extensions import Self


class WorkflowContainerConfig(BaseModel):
    """
    WorkflowContainerConfig
    """  # noqa: E501

    subgraph_id: StrictStr = Field(description="Identifier of the subgraph definition to run.", alias="subgraphId")
    loop: Optional[WorkflowContainerLoopPolicy] = None
    retry: Optional[WorkflowContainerRetryPolicy] = None
    timeout_seconds: Optional[int] = Field(default=None, alias="timeoutSeconds")
    notes: Optional[StrictStr] = None
    __properties: ClassVar[list[str]] = ["subgraphId", "loop", "retry", "timeoutSeconds", "notes"]

    model_config = {
        "populate_by_name": True,
        "validate_assignment": True,
        "protected_namespaces": (),
    }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> Self:
        return cls.from_dict(json.loads(json_str))

    def to_dict(self) -> Dict[str, Any]:
        _dict = self.model_dump(by_alias=True, exclude_none=True, exclude={"loop", "retry"})
        if self.loop:
            _dict["loop"] = self.loop.to_dict()
        if self.retry:
            _dict["retry"] = self.retry.to_dict()
        return _dict

    @classmethod
    def from_dict(cls, obj: Dict[str, Any]) -> Self:
        if obj is None:
            return None
        if not isinstance(obj, dict):
            return cls.model_validate(obj)
        return cls.model_validate(
            {
                "subgraphId": obj.get("subgraphId"),
                "loop": WorkflowContainerLoopPolicy.from_dict(obj.get("loop")) if obj.get("loop") is not None else None,
                "retry": WorkflowContainerRetryPolicy.from_dict(obj.get("retry")) if obj.get("retry") is not None else None,
                "timeoutSeconds": obj.get("timeoutSeconds"),
                "notes": obj.get("notes"),
            }
        )

