"""Facade for resource-related services."""

from __future__ import annotations

from functools import lru_cache

from .package_permissions import PackagePermissionService
from .package_vault import PackageVaultService
from .resources import ResourceService


class ResourceServiceFacade:
    def __init__(self) -> None:
        self.resources = ResourceService()
        self.package_permissions = PackagePermissionService()
        self.package_vault = PackageVaultService()


@lru_cache()
def get_resource_service_facade() -> ResourceServiceFacade:
    return ResourceServiceFacade()


resource_services = get_resource_service_facade()

__all__ = ["ResourceServiceFacade", "get_resource_service_facade", "resource_services"]
