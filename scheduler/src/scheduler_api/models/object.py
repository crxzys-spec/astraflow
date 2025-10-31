"""Minimal pydantic-compatible base class for OpenAPI `object` schemas."""

from __future__ import annotations

from typing import Any, Dict

from pydantic import BaseModel, ConfigDict


class object(BaseModel):  # noqa: N801  (align with generated imports)
    """Acts as a flexible container allowing arbitrary extra properties."""

    model_config = ConfigDict(
        extra="allow",
        validate_assignment=True,
        arbitrary_types_allowed=True,
        protected_namespaces=(),
    )

    def __getattr__(self, item: str) -> Any:
        try:
            return self.__dict__[item]
        except KeyError as exc:  # pragma: no cover
            raise AttributeError(item) from exc

    def __delattr__(self, item: str) -> None:
        try:
            del self.__dict__[item]
        except KeyError as exc:  # pragma: no cover
            raise AttributeError(item) from exc

    def to_dict(self) -> Dict[str, Any]:
        """Drop-in helper mirroring the generated models."""
        return self.model_dump()
