"""Domain models for resource access and vault items."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


@dataclass
class StoredPackagePermission:
    permission_id: str
    owner_id: str
    package_name: str
    permission_key: str
    types: List[str]
    actions: List[str]
    created_at: datetime
    providers: Optional[List[str]] = None

    def to_dict(self) -> dict:
        return {
            "permission_id": self.permission_id,
            "owner_id": self.owner_id,
            "package_name": self.package_name,
            "permission_key": self.permission_key,
            "types": list(self.types),
            "providers": list(self.providers or []),
            "actions": list(self.actions),
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class StoredPackageVaultItem:
    item_id: str
    owner_id: str
    package_name: str
    key: str
    value: str
    created_at: datetime
    updated_at: datetime

    def to_dict(self) -> dict:
        return {
            "item_id": self.item_id,
            "owner_id": self.owner_id,
            "package_name": self.package_name,
            "key": self.key,
            "value": self.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
