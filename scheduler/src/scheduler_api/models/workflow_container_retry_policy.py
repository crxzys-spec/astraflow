# coding: utf-8

"""
    Scheduler Public API (v1)
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field
from typing import Any, ClassVar, Dict, Optional
try:
    from typing import Self
except ImportError:
    from typing_extensions import Self


class WorkflowContainerRetryPolicy(BaseModel):
    """
    Retry policy applied when a container subgraph fails.
    """  # noqa: E501

    max_attempts: Optional[int] = Field(default=None, description="Maximum number of attempts.", alias="maxAttempts")
    backoff_seconds: Optional[int] = Field(default=None, description="Backoff delay in seconds between attempts.", alias="backoffSeconds")
    __properties: ClassVar[list[str]] = ["maxAttempts", "backoffSeconds"]

    model_config = {
        "populate_by_name": True,
        "validate_assignment": True,
        "protected_namespaces": (),
    }

    def to_json(self) -> str:
        return self.model_dump_json(by_alias=True, exclude_none=True)

    @classmethod
    def from_json(cls, json_str: str) -> Self:
        return cls.model_validate_json(json_str)

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump(by_alias=True, exclude_none=True)

    @classmethod
    def from_dict(cls, obj: Dict[str, Any]) -> Self:
        if obj is None:
            return None
        if not isinstance(obj, dict):
            return cls.model_validate(obj)
        return cls.model_validate(obj)

