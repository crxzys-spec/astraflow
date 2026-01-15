"""Manifest-backed package catalog."""

from __future__ import annotations

from pathlib import Path
import json
from threading import RLock
from typing import Dict, List, Tuple

from shared.models.manifest import Node, PackageManifest
from scheduler_api.infra.catalog.hub_link import HUB_LINK_FILENAME, read_hub_link
from scheduler_api.config.settings import get_api_settings

LOCAL_OWNER = "local"
I18N_PREFIX = "@i18n:"


class PackageCatalogError(Exception):
    """Base error for package catalog operations."""


class PackageNotFoundError(PackageCatalogError):
    """Raised when the package name is unknown."""


class PackageVersionNotFoundError(PackageCatalogError):
    """Raised when the requested package version is unavailable."""


def _default_packages_root() -> Path:
    return get_api_settings().packages_root


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


def _normalize_locale(locale: str) -> str:
    return locale.lower().replace("_", "-")


def _load_locale_packs(version_dir: Path) -> Dict[str, Dict[str, str]]:
    locales_dir = version_dir / "locales"
    packs: Dict[str, Dict[str, str]] = {}
    if not locales_dir.is_dir():
        return packs
    for locale_path in locales_dir.glob("*.json"):
        locale = locale_path.stem
        try:
            payload = json.loads(locale_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(payload, dict):
            packs[locale] = {
                str(key): str(value) for key, value in payload.items()
            }
    return packs


def _resolve_i18n_value(value: object, packs: Dict[str, Dict[str, str]]):
    if not isinstance(value, str) or not value.startswith(I18N_PREFIX):
        return value
    key = value[len(I18N_PREFIX) :]
    if not packs:
        return value
    normalized = {
        _normalize_locale(locale): (locale, entries)
        for locale, entries in packs.items()
    }
    fallback = None
    for candidate in ("en", "en-us"):
        _, entries = normalized.get(candidate, (None, {}))
        if entries:
            fallback = entries.get(key)
            if fallback:
                break
    resolved: Dict[str, str] = {}
    for locale, entries in packs.items():
        resolved[locale] = entries.get(key) or fallback or key
    return resolved


def _apply_i18n_to_manifest(payload: Dict[str, object], packs: Dict[str, Dict[str, str]]):
    def apply(value):
        return _resolve_i18n_value(value, packs)

    if "displayName" in payload:
        payload["displayName"] = apply(payload.get("displayName"))
    if "description" in payload:
        payload["description"] = apply(payload.get("description"))

    for adapter in payload.get("adapters", []) or []:
        if isinstance(adapter, dict) and "description" in adapter:
            adapter["description"] = apply(adapter.get("description"))

    requirements = payload.get("requirements") or {}
    if isinstance(requirements, dict):
        for group in ("resources", "vault", "permissions"):
            for req in requirements.get(group, []) or []:
                if not isinstance(req, dict):
                    continue
                if "label" in req:
                    req["label"] = apply(req.get("label"))
                if "description" in req:
                    req["description"] = apply(req.get("description"))

    for node in payload.get("nodes", []) or []:
        if not isinstance(node, dict):
            continue
        for key in ("category", "label", "description"):
            if key in node:
                node[key] = apply(node.get(key))
        ui = node.get("ui") or {}
        if not isinstance(ui, dict):
            continue
        for port_group in ("inputPorts", "outputPorts", "ports"):
            for port in ui.get(port_group, []) or []:
                if not isinstance(port, dict):
                    continue
                if "label" in port:
                    port["label"] = apply(port.get("label"))
                if "description" in port:
                    port["description"] = apply(port.get("description"))
        for widget in ui.get("widgets", []) or []:
            if isinstance(widget, dict) and "label" in widget:
                widget["label"] = apply(widget.get("label"))


class PackageCatalog:
    """Loads manifests from disk and offers lookup helpers."""

    def __init__(self, packages_root: Path | None = None) -> None:
        root = Path(packages_root) if packages_root else _default_packages_root()
        self._root = root.expanduser().resolve()
        self._lock = RLock()
        self._manifests: Dict[Tuple[str, str, str], PackageManifest] = {}
        self._node_index: Dict[Tuple[str, str, str, str], Node] = {}
        self._hub_links: Dict[Tuple[str, str, str], Dict[str, object]] = {}

    @staticmethod
    def _split_owner_name(value: str) -> Tuple[str | None, str]:
        raw = value.strip()
        if "/" in raw:
            owner, name = raw.split("/", 1)
            if owner and name:
                return owner, name
        return None, raw

    def _resolve_owner_name(self, name: str, owner: str | None = None) -> Tuple[str, str]:
        owner_hint, package_name = self._split_owner_name(name)
        if owner_hint:
            return owner_hint, package_name
        if owner:
            return owner, package_name
        owners = {key[0] for key in self._manifests.keys() if key[1] == package_name}
        if not owners:
            raise PackageNotFoundError(f"Package '{package_name}' not found")
        if LOCAL_OWNER in owners:
            return LOCAL_OWNER, package_name
        if len(owners) == 1:
            return owners.pop(), package_name
        raise PackageCatalogError("Package owner is required.")

    @staticmethod
    def _is_legacy_package_dir(owner_dir: Path) -> bool:
        for child in owner_dir.iterdir():
            if not child.is_dir():
                continue
            if (child / "manifest.json").is_file():
                return True
        return False

    @property
    def packages_root(self) -> Path:
        return self._root

    def reload(self) -> None:
        manifests: Dict[Tuple[str, str, str], PackageManifest] = {}
        node_index: Dict[Tuple[str, str, str, str], Node] = {}
        hub_links: Dict[Tuple[str, str, str], Dict[str, object]] = {}

        root = self._root
        if not root.exists():
            with self._lock:
                self._manifests = {}
                self._node_index = {}
            return

        def _scan_package_dir(owner: str, package_dir: Path) -> None:
            for version_dir in package_dir.iterdir():
                manifest_path = version_dir / "manifest.json"
                if not manifest_path.is_file():
                    continue
                try:
                    manifest_payload = json.loads(
                        manifest_path.read_text(encoding="utf-8")
                    )
                except Exception:
                    continue
                locale_packs = _load_locale_packs(version_dir)
                _apply_i18n_to_manifest(manifest_payload, locale_packs)
                manifest = PackageManifest.model_validate(manifest_payload)
                key = (owner, manifest.name, manifest.version)
                manifests[key] = manifest
                hub_link = read_hub_link(version_dir / HUB_LINK_FILENAME)
                if hub_link:
                    hub_links[key] = hub_link
                for node in manifest.nodes:
                    node_index[(owner, manifest.name, manifest.version, node.type)] = node

        for owner_dir in root.iterdir():
            if not owner_dir.is_dir():
                continue
            if self._is_legacy_package_dir(owner_dir):
                _scan_package_dir(LOCAL_OWNER, owner_dir)
                continue
            for package_dir in owner_dir.iterdir():
                if not package_dir.is_dir():
                    continue
                _scan_package_dir(owner_dir.name, package_dir)

        with self._lock:
            self._manifests = manifests
            self._node_index = node_index
            self._hub_links = hub_links

    def list_packages(self) -> List[Dict[str, object]]:
        with self._lock:
            items = list(self._manifests.items())
            hub_links = dict(self._hub_links)

        grouped: Dict[Tuple[str, str], List[PackageManifest]] = {}
        for (owner, _, _), manifest in items:
            grouped.setdefault((owner, manifest.name), []).append(manifest)

        summaries: List[Dict[str, object]] = []
        for (owner, name), manifests in grouped.items():
            versions = sorted((m.version for m in manifests), key=_version_key, reverse=True)
            latest = max(manifests, key=lambda manifest: _version_key(manifest.version))
            hub_versions = sorted(
                [
                    version
                    for (hub_owner, pkg, version) in hub_links.keys()
                    if hub_owner == owner and pkg == name
                ],
                key=_version_key,
                reverse=True,
            )
            latest_hub = hub_links.get((owner, name, versions[0])) if versions else None
            summaries.append(
                {
                    "name": name,
                    "description": latest.description,
                    "latestVersion": versions[0] if versions else None,
                    "defaultVersion": versions[0] if versions else None,
                    "versions": versions,
                    "ownerId": owner,
                    "hub": latest_hub,
                    "hubVersions": hub_versions or None,
                }
            )
        summaries.sort(key=lambda item: (item.get("name"), item.get("ownerId")))
        return summaries

    def list_versions(self, name: str, owner: str | None = None) -> List[str]:
        resolved_owner, resolved_name = self._resolve_owner_name(name, owner)
        with self._lock:
            versions = [
                version
                for (pkg_owner, pkg_name, version) in self._manifests.keys()
                if pkg_owner == resolved_owner and pkg_name == resolved_name
            ]
        return sorted(versions, key=_version_key, reverse=True)

    def get_manifest(
        self,
        name: str,
        version: str,
        *,
        owner: str | None = None,
    ) -> PackageManifest:
        resolved_owner, resolved_name = self._resolve_owner_name(name, owner)
        with self._lock:
            manifest = self._manifests.get((resolved_owner, resolved_name, version))
        if not manifest:
            names = {pkg_name for (_, pkg_name, _) in self._manifests.keys()}
            if resolved_name not in names:
                raise PackageNotFoundError(f"Package '{resolved_name}' not found")
            raise PackageVersionNotFoundError(
                f"Package '{resolved_name}' has no version '{version}'"
            )
        return manifest.model_copy(deep=True)

    def get_package_detail(
        self,
        name: str,
        version: str | None = None,
        *,
        owner: str | None = None,
    ) -> Dict[str, object]:
        resolved_owner, resolved_name = self._resolve_owner_name(name, owner)
        versions = self.list_versions(resolved_name, owner=resolved_owner)
        if not versions:
            raise PackageNotFoundError(f"Package '{resolved_name}' not found")
        target_version = version or versions[0]
        manifest = self.get_manifest(resolved_name, target_version, owner=resolved_owner)
        with self._lock:
            hub_link = self._hub_links.get((resolved_owner, resolved_name, target_version))
        return {
            "name": resolved_name,
            "version": target_version,
            "availableVersions": versions,
            "manifest": manifest,
            "hub": hub_link,
            "ownerId": resolved_owner,
        }

    def resolve_node(
        self,
        name: str,
        version: str,
        node_type: str,
        *,
        owner: str | None = None,
    ) -> Node:
        resolved_owner, resolved_name = self._resolve_owner_name(name, owner)
        with self._lock:
            node = self._node_index.get((resolved_owner, resolved_name, version, node_type))
        if not node:
            raise PackageVersionNotFoundError(
                f"Node '{node_type}' not found in package '{resolved_name}' version '{version}'"
            )
        return node.model_copy(deep=True)


catalog = PackageCatalog()


