# coding: utf-8

from typing import List

from pydantic import BaseModel, Field


class TokenModel(BaseModel):
    """Defines a token model for downstream role enforcement."""

    sub: str
    roles: List[str] = Field(default_factory=list)
