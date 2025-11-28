"""Adapter registry for package-provided handlers."""

from __future__ import annotations

import importlib
import logging
from dataclasses import dataclass
from types import ModuleType
from typing import Any, Callable, Dict, Optional, Tuple

LOGGER = logging.getLogger(__name__)

HandlerCallable = Callable[..., Any]
RegistryKey = Tuple[str, str, str]  # (package_name, package_version, handler_key)


@dataclass
class HandlerDescriptor:
    package: str
    version: str
    handler: str
    callable: HandlerCallable
    metadata: Dict[str, Any]


class AdapterRegistry:
    """In-memory registry of package handlers resolved from manifests."""

    def __init__(self) -> None:
        self._handlers: Dict[RegistryKey, HandlerDescriptor] = {}

    def register(
        self,
        package: str,
        version: str,
        handler_key: str,
        entrypoint: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> HandlerDescriptor:
        """Import and register a handler entrypoint."""

        module_name, attr = self._split_entrypoint(entrypoint)
        module: ModuleType = importlib.import_module(module_name)
        handler_callable = getattr(module, attr)
        descriptor = HandlerDescriptor(
            package=package,
            version=version,
            handler=handler_key,
            callable=handler_callable,
            metadata=metadata or {},
        )
        self._handlers[(package, version, handler_key)] = descriptor
        LOGGER.debug("Registered handler %s@%s:%s -> %s", package, version, handler_key, entrypoint)
        return descriptor

    def register_callable(
        self,
        package: str,
        version: str,
        handler_key: str,
        handler_callable: HandlerCallable,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> HandlerDescriptor:
        """Register an already-loaded handler callable."""
        descriptor = HandlerDescriptor(
            package=package,
            version=version,
            handler=handler_key,
            callable=handler_callable,
            metadata=metadata or {},
        )
        self._handlers[(package, version, handler_key)] = descriptor
        LOGGER.debug("Registered handler %s@%s:%s (callable)", package, version, handler_key)
        return descriptor

    def unregister(self, package: str, version: str) -> None:
        """Remove all handlers associated with the package version."""

        to_remove = [key for key in self._handlers if key[0] == package and key[1] == version]
        for key in to_remove:
            LOGGER.debug("Unregistering handler %s", key)
            self._handlers.pop(key, None)

    def resolve(self, package: str, version: str, handler_key: str) -> HandlerDescriptor:
        """Retrieve a registered handler; raise if missing."""

        key = (package, version, handler_key)
        try:
            return self._handlers[key]
        except KeyError as exc:
            available = ", ".join(f"{pkg}@{ver}:{handler}" for (pkg, ver, handler) in self._handlers.keys())
            LOGGER.error("Handler not registered: %s (available: %s)", key, available or "none")
            raise KeyError(f"Handler not registered: {key}") from exc

    def list_handlers(self) -> Dict[RegistryKey, HandlerDescriptor]:
        """Expose current handler mappings (read-only)."""

        return dict(self._handlers)

    @staticmethod
    def _split_entrypoint(entrypoint: str) -> Tuple[str, str]:
        if ":" not in entrypoint:
            raise ValueError(f"Invalid entrypoint '{entrypoint}', expected format 'module:attr'")
        module_name, attr = entrypoint.split(":", 1)
        return module_name, attr
