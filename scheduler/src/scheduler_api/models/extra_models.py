# coding: utf-8

from typing import List, Optional

from pydantic import BaseModel, Field


class TokenModel(BaseModel):
    """Defines a token model."""

    sub: str
    username: str
    display_name: Optional[str] = None
    roles: List[str] = Field(default_factory=list)
