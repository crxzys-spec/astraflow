"""ORM model for DB-backed resource payloads."""

from __future__ import annotations

from sqlalchemy import LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base


class ResourcePayloadRecord(Base):
    __tablename__ = "resource_payloads"

    resource_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    payload: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
