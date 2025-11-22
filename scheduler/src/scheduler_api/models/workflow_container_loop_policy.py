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


class WorkflowContainerLoopPolicy(BaseModel):
    """
    Execution policy describing how a container node loops over its subgraph.
    """  # noqa: E501

    enabled: Optional[bool] = Field(default=None, description="Whether loop execution is enabled.")
    max_iterations: Optional[int] = Field(default=None, description="Maximum number of iterations to run.", alias="maxIterations")
    condition: Optional[str] = Field(default=None, description="Expression evaluated against container results/parameters to exit the loop.")
    __properties: ClassVar[list[str]] = ["enabled", "maxIterations", "condition"]

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

