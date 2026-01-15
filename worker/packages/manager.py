"""Package installation workflows."""

from __future__ import annotations

import json
import hashlib
import logging
import shutil
import sys
import tempfile
import importlib.machinery
import importlib.util
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable
from urllib.parse import urlparse
from urllib.request import urlretrieve

from worker.config import WorkerSettings
from .registry import AdapterRegistry

LOGGER = logging.getLogger(__name__)
I18N_PREFIX = "@i18n:"


def _normalize_locale(locale: str) -> str:
    return locale.lower().replace("_", "-")


def _load_locale_packs(package_dir: Path) -> dict[str, dict[str, str]]:
    locales_dir = package_dir / "locales"
    packs: dict[str, dict[str, str]] = {}
    if not locales_dir.is_dir():
        return packs
    for locale_path in locales_dir.glob("*.json"):
        locale = locale_path.stem
        try:
            payload = json.loads(locale_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(payload, dict):
            packs[locale] = {str(key): str(value) for key, value in payload.items()}
    return packs


def _resolve_i18n_value(value: object, packs: dict[str, dict[str, str]]):
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
    resolved: dict[str, str] = {}
    for locale, entries in packs.items():
        resolved[locale] = entries.get(key) or fallback or key
    return resolved


def _apply_i18n_to_manifest(
    payload: dict[str, Any],
    packs: dict[str, dict[str, str]],
) -> None:
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


@dataclass
class PackageDescriptor:
    name: str
    version: str
    manifest: Dict[str, Any]


class PackageManager:
    """Install/uninstall package archives and refresh the adapter registry."""

    def __init__(self, settings: WorkerSettings, registry: AdapterRegistry) -> None:
        self._settings = settings
        self._registry = registry
        self.packages_root.mkdir(parents=True, exist_ok=True)

    @property
    def packages_root(self) -> Path:
        return self._settings.packages_dir

    def install(self, name: str, version: str, url: str, checksum: str | None = None) -> PackageDescriptor:
        """Download, extract, validate, and register a package."""

        LOGGER.info("Installing package %s@%s from %s", name, version, url)
        tmp_dir = Path(tempfile.mkdtemp(prefix="pkginstall-"))
        try:
            archive_path = self._download(url, tmp_dir)
            if checksum:
                self._verify_checksum(archive_path, checksum)
            package_dir = self.packages_root / name
            self._clear_directory(package_dir)
            self._extract_archive(archive_path, package_dir)
            manifest = self._load_manifest(package_dir)
            self._validate_manifest(manifest, name, version)
            self._register_handlers(package_dir, manifest)
            LOGGER.info("Package %s@%s installed with %d handlers", name, version, len(manifest.get("adapters", [])))
            return PackageDescriptor(name=name, version=version, manifest=manifest)
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def uninstall(self, name: str, version: str) -> None:
        """Remove a package and unregister its handlers."""

        package_dir = self._resolve_installed_dir(name, version)
        LOGGER.info("Uninstalling package %s@%s", name, version)
        if package_dir and package_dir.exists():
            shutil.rmtree(package_dir)
        self._registry.unregister(name, version)

    def list_installed(self) -> Iterable[Path]:
        """Enumerate installed package directories."""

        root = self.packages_root
        if not root.exists():
            return []
        return self._iter_installed_dirs(root)

    def collect_inventory(self) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """List installed packages and register handlers for control-plane registration."""

        inventory: list[dict[str, Any]] = []
        manifest_payloads: list[dict[str, Any]] = []
        for package_path in self.list_installed():
            package_dir = Path(package_path)
            try:
                manifest = self._load_manifest(package_dir)
            except Exception as exc:  # noqa: BLE001
                LOGGER.warning("Failed to load manifest from %s: %s", package_dir, exc)
                continue
            name = manifest.get("name") or package_dir.name
            version = manifest.get("version") or "unknown"
            try:
                self._register_handlers(package_dir, manifest)
            except Exception as exc:  # noqa: BLE001
                LOGGER.warning("Failed to register handlers for %s@%s: %s", name, version, exc)
            inventory.append({"name": name, "version": version, "status": "installed"})
            manifest_payloads.append({"name": name, "version": version, "manifest": manifest})
        return inventory, manifest_payloads

    def _download(self, url: str, dest: Path) -> Path:
        parsed = urlparse(url)
        if parsed.scheme in {"file", ""}:
            return Path(parsed.path)
        local_path = dest / "package.cwx"
        LOGGER.debug("Downloading package archive from %s", url)
        urlretrieve(url, local_path)
        return local_path

    @staticmethod
    def _verify_checksum(archive_path: Path, checksum: str) -> None:
        expected = checksum.strip().lower()
        if expected.startswith("sha256:"):
            expected = expected.split("sha256:", 1)[1]
        if not expected:
            return
        digest = hashlib.sha256()
        with archive_path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        actual = digest.hexdigest()
        if actual != expected:
            raise ValueError(
                f"Package checksum mismatch: expected {expected}, got {actual}"
            )

    def _clear_directory(self, target_dir: Path) -> None:
        if target_dir.exists():
            shutil.rmtree(target_dir)
        target_dir.mkdir(parents=True, exist_ok=True)

    def _extract_archive(self, archive_path: Path, target_dir: Path) -> None:
        LOGGER.debug("Extracting archive %s to %s", archive_path, target_dir)
        shutil.unpack_archive(str(archive_path), str(target_dir))

    def _iter_installed_dirs(self, root: Path) -> Iterable[Path]:
        def iter_dirs() -> Iterable[Path]:
            for candidate in root.iterdir():
                if not candidate.is_dir():
                    continue
                manifest_path = candidate / "manifest.json"
                if manifest_path.is_file():
                    yield candidate
                    continue
                for package_dir in candidate.iterdir():
                    if not package_dir.is_dir():
                        continue
                    sub_manifest = package_dir / "manifest.json"
                    if sub_manifest.is_file():
                        yield package_dir
                        continue
                    for version_dir in package_dir.iterdir():
                        if not version_dir.is_dir():
                            continue
                        version_manifest = version_dir / "manifest.json"
                        if version_manifest.is_file():
                            yield version_dir
        return iter_dirs()

    def _resolve_installed_dir(self, name: str, version: str) -> Path | None:
        for package_dir in self.list_installed():
            try:
                manifest = self._load_manifest(Path(package_dir))
            except FileNotFoundError:
                continue
            if manifest.get("name") == name and manifest.get("version") == version:
                return Path(package_dir)
        direct = self.packages_root / name / version
        if (direct / "manifest.json").is_file():
            return direct
        return None

    @staticmethod
    def _load_manifest(package_dir: Path) -> Dict[str, Any]:
        manifest_path = package_dir / "manifest.json"
        with manifest_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if isinstance(payload, dict):
            _apply_i18n_to_manifest(payload, _load_locale_packs(package_dir))
        return payload

    @staticmethod
    def _validate_manifest(manifest: Dict[str, Any], expected_name: str, expected_version: str) -> None:
        if manifest.get("name") != expected_name:
            raise ValueError(f"Manifest name mismatch: {manifest.get('name')} != {expected_name}")
        if manifest.get("version") != expected_version:
            raise ValueError(f"Manifest version mismatch: {manifest.get('version')} != {expected_version}")

    def _register_handlers(self, package_dir: Path, manifest: Dict[str, Any]) -> None:
        package_name = manifest["name"]
        version = manifest["version"]
        # Ensure the package modules are importable during handler registration.
        package_sys_path = str(package_dir)
        if package_sys_path not in sys.path:
            sys.path.insert(0, package_sys_path)

        adapter_entrypoints: dict[str, str] = {}
        adapter_metadata: dict[str, dict[str, Any]] = {}
        adapters = manifest.get("adapters", [])
        for adapter in adapters:
            entrypoint = adapter.get("entrypoint")
            name = adapter.get("name")
            if not entrypoint or not name:
                LOGGER.warning("Skipping adapter with missing name/entrypoint: %s", adapter)
                continue
            adapter_entrypoints[name] = entrypoint
            adapter_metadata[name] = adapter.get("metadata", {})

        nodes = manifest.get("nodes", [])
        for node in nodes:
            adapter_name = node.get("adapter")
            handler_name = node.get("handler")
            node_type = node.get("type")
            if not adapter_name or not handler_name or not node_type:
                LOGGER.warning("Skipping node with missing adapter/handler/type: %s", node)
                continue
            entrypoint = adapter_entrypoints.get(adapter_name)
            if not entrypoint:
                LOGGER.warning(
                    "Node %s references unknown adapter %s", node_type, adapter_name
                )
                continue
            resolved_entrypoint = self._build_entrypoint(entrypoint, handler_name)
            metadata = dict(adapter_metadata.get(adapter_name, {}))
            metadata.update(
                {
                    "node": node_type,
                    "adapter": adapter_name,
                    "config": node.get("config", {}),
                }
            )
            LOGGER.info(
                "Registering handler %s@%s:%s -> %s",
                package_name,
                version,
                node_type,
                resolved_entrypoint,
            )
            handler_callable = self._load_handler(package_dir, resolved_entrypoint)
            self._registry.register_callable(
                package_name,
                version,
                node_type,
                handler_callable,
                metadata=metadata,
            )

    @staticmethod
    def _build_entrypoint(module_path: str, handler_name: str) -> str:
        if ":" in module_path:
            module_name, base_attr = module_path.split(":", 1)
            target_attr = (
                base_attr if base_attr.split(".")[-1] == handler_name else f"{base_attr}.{handler_name}"
            )
            return f"{module_name}:{target_attr}"
        return f"{module_path}:{handler_name}"

    def _load_handler(self, package_dir: Path, entrypoint: str):
        module_name, attr = AdapterRegistry._split_entrypoint(entrypoint)
        module_path = module_name.replace(".", "/")
        module_file = package_dir / f"{module_path}.py"
        if not module_file.is_file():
            # try package directory form
            module_file = package_dir / module_path / "__init__.py"
        if not module_file.is_file():
            raise ModuleNotFoundError(f"Cannot resolve entrypoint {entrypoint} in {package_dir}")
        alias = f"{package_dir.name}_{module_name}".replace(".", "_").replace("-", "_")
        spec = importlib.util.spec_from_file_location(alias, module_file)
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load spec for {module_file}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[alias] = module
        spec.loader.exec_module(module)
        return getattr(module, attr)
