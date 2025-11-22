# coding: utf-8

"""
    Scheduler Public API (v1)

    Localized workflow snapshot embedded as a reusable subgraph.
"""

from __future__ import annotations

import json
from typing import Any, ClassVar, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field, StrictStr

from scheduler_api.models.workflow_subgraph_metadata import WorkflowSubgraphMetadata

try:
    from typing import Self
except ImportError:
    from typing_extensions import Self


class WorkflowSubgraph(BaseModel):
    """
    WorkflowSubgraph
    """  # noqa: E501

    id: StrictStr = Field(description="Stable identifier referenced by container nodes.")
    definition: Dict[str, Any] = Field(description="Localized workflow snapshot backing this subgraph.")
    metadata: Optional[WorkflowSubgraphMetadata] = None
    __properties: ClassVar[list[str]] = ["id", "definition", "metadata"]

    model_config = {
        "populate_by_name": True,
        "validate_assignment": True,
        "protected_namespaces": (),
    }

    def to_str(self) -> str:
        """Returns the string representation of the model using alias"""
        return self.__repr__()

    def to_json(self) -> str:
        """Returns the JSON representation of the model using alias"""
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> Self:
        """Create an instance of WorkflowSubgraph from a JSON string"""
        return cls.from_dict(json.loads(json_str))

    def to_dict(self) -> Dict[str, Any]:
        """Return the dictionary representation of the model using alias."""
        _dict = self.model_dump(
            by_alias=True,
            exclude={
                "metadata",
            },
            exclude_none=True,
        )
        if self.metadata:
            _dict["metadata"] = self.metadata.to_dict()
        return _dict

    @classmethod
    def from_dict(cls, obj: Dict[str, Any]) -> Self:
        """Create an instance of WorkflowSubgraph from a dict"""
        if obj is None:
            return None
        if not isinstance(obj, dict):
            return cls.model_validate(obj)
        metadata = obj.get("metadata")
        return cls.model_validate(
            {
                "id": obj.get("id"),
                "definition": obj.get("definition"),
                "metadata": WorkflowSubgraphMetadata.from_dict(metadata) if metadata is not None else None,
            }
        )

