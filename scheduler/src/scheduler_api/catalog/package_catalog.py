"""Manifest-backed package catalog."""

from __future__ import annotations

import os
from pathlib import Path
from threading import RLock
from typing import Dict, List, Tuple

from shared.models.manifest import Node, PackageManifest


class PackageCatalogError(Exception):
    """Base error for package catalog operations."""


class PackageNotFoundError(PackageCatalogError):
    """Raised when the package name is unknown."""


class PackageVersionNotFoundError(PackageCatalogError):
    """Raised when the requested package version is unavailable."""


def _default_packages_root() -> Path:
    base = Path(__file__).resolve().parents[4]
    env_root = os.getenv("ASTRA_PACKAGES_ROOT")
    root = Path(env_root) if env_root else base / "node-packages"
    return root.expanduser().resolve()


def _version_key(value: str):
    try:
        from packaging.version import Version  # type: ignore
    except Exception:  # pragma: no cover
        main, _, suffix = value.partition("-")
        parts: List[object] = [int(part) if part.isdigit() else part for part in main.split(".")]
        if suffix:
            parts.append(suffix)
        return tuple(parts)
    else:
        return Version(value)


class PackageCatalog:
    """Loads manifests from disk and offers lookup helpers."""

    def __init__(self, packages_root: Path | None = None) -> None:
        self._root = Path(packages_root) if packages_root else _default_packages_root()
        self._lock = RLock()
        self._manifests: Dict[Tuple[str, str], PackageManifest] = {}
        self._node_index: Dict[Tuple[str, str, str], Node] = {}

    @property
    def packages_root(self) -> Path:
        return self._root

    def reload(self) -> None:
        manifests: Dict[Tuple[str, str], PackageManifest] = {}
        node_index: Dict[Tuple[str, str, str], Node] = {}

        root = self._root
        if not root.exists():
            with self._lock:
                self._manifests = {}
                self._node_index = {}
            return

        for package_dir in root.iterdir():
            if not package_dir.is_dir():
                continue
            for version_dir in package_dir.iterdir():
                manifest_path = version_dir / "manifest.json"
                if not manifest_path.is_file():
                    continue
                manifest = PackageManifest.model_validate_json(
                    manifest_path.read_text(encoding="utf-8")
                )
                key = (manifest.name, manifest.version)
                manifests[key] = manifest
                for node in manifest.nodes:
                    node_index[(manifest.name, manifest.version, node.type)] = node

        with self._lock:
            self._manifests = manifests
            self._node_index = node_index

    def list_packages(self) -> List[Dict[str, object]]:
        with self._lock:
            items = list(self._manifests.items())

        grouped: Dict[str, List[PackageManifest]] = {}
        for (_, _), manifest in items:
            grouped.setdefault(manifest.name, []).append(manifest)

        summaries: List[Dict[str, object]] = []
        for name, manifests in grouped.items():
            versions = sorted((m.version for m in manifests), key=_version_key, reverse=True)
            latest = max(manifests, key=lambda manifest: _version_key(manifest.version))
            summaries.append(
                {
                    "name": name,
                    "description": latest.description,
                    "latestVersion": versions[0] if versions else None,
                    "defaultVersion": versions[0] if versions else None,
                    "versions": versions,
                }
            )
        summaries.sort(key=lambda item: item["name"])
        return summaries

    def list_versions(self, name: str) -> List[str]:
        with self._lock:
            versions = [version for (pkg, version) in self._manifests.keys() if pkg == name]
        return sorted(versions, key=_version_key, reverse=True)

    def get_manifest(self, name: str, version: str) -> PackageManifest:
        with self._lock:
            manifest = self._manifests.get((name, version))
        if not manifest:
            if name not in {pkg for pkg, _ in self._manifests}:
                raise PackageNotFoundError(f"Package '{name}' not found")
            raise PackageVersionNotFoundError(f"Package '{name}' has no version '{version}'")
        return manifest.model_copy(deep=True)

    def get_package_detail(self, name: str, version: str | None = None) -> Dict[str, object]:
        versions = self.list_versions(name)
        if not versions:
            raise PackageNotFoundError(f"Package '{name}' not found")
        target_version = version or versions[0]
        manifest = self.get_manifest(name, target_version)
        return {
            "name": name,
            "version": target_version,
            "availableVersions": versions,
            "manifest": manifest,
        }

    def resolve_node(self, name: str, version: str, node_type: str) -> Node:
        with self._lock:
            node = self._node_index.get((name, version, node_type))
        if not node:
            raise PackageVersionNotFoundError(
                f"Node '{node_type}' not found in package '{name}' version '{version}'"
            )
        return node.model_copy(deep=True)


catalog = PackageCatalog()


