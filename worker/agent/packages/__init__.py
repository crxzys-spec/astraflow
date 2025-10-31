"""Package management primitives."""

from .manager import PackageManager
from .registry import AdapterRegistry, HandlerDescriptor

__all__ = ["PackageManager", "AdapterRegistry", "HandlerDescriptor"]
