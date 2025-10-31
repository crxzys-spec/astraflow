"""Package installation workflows."""

from __future__ import annotations

import json
import logging
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable
from urllib.parse import urlparse
from urllib.request import urlretrieve

from ..config import WorkerSettings
from .registry import AdapterRegistry

LOGGER = logging.getLogger(__name__)


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

    def _download(self, url: str, dest: Path) -> Path:
        parsed = urlparse(url)
        if parsed.scheme in {"file", ""}:
            return Path(parsed.path)
        local_path = dest / "package.cwx"
        LOGGER.debug("Downloading package archive from %s", url)
        urlretrieve(url, local_path)
        return local_path

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
                for subdir in candidate.iterdir():
                    sub_manifest = subdir / "manifest.json"
                    if subdir.is_dir() and sub_manifest.is_file():
                        yield subdir
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
            return json.load(handle)

    @staticmethod
    def _validate_manifest(manifest: Dict[str, Any], expected_name: str, expected_version: str) -> None:
        if manifest.get("name") != expected_name:
            raise ValueError(f"Manifest name mismatch: {manifest.get('name')} != {expected_name}")
        if manifest.get("version") != expected_version:
            raise ValueError(f"Manifest version mismatch: {manifest.get('version')} != {expected_version}")

    def _register_handlers(self, package_dir: Path, manifest: Dict[str, Any]) -> None:
        package_name = manifest["name"]
        version = manifest["version"]
        adapters = manifest.get("adapters", [])
        for adapter in adapters:
            entrypoint = adapter.get("entrypoint")
            runtime = adapter.get("runtime")
            capabilities = adapter.get("capabilities", [])
            metadata = adapter.get("metadata", {})
            for capability in capabilities:
                handler_key = capability
                self._registry.register(package_name, version, handler_key, entrypoint, metadata=metadata | {"runtime": runtime})
        nodes = manifest.get("nodes", [])
        for node in nodes:
            runtimes = node.get("runtimes", {})
            for runtime_name, runtime_cfg in runtimes.items():
                handler_key = f"{node.get('type')}::{runtime_name}"
                handler_name = runtime_cfg.get("handler")
                if handler_name:
                    entrypoint = self._resolve_node_entrypoint(manifest, runtime_name, handler_name)
                    self._registry.register(package_name, version, handler_key, entrypoint, metadata={"node": node.get("type")})

    @staticmethod
    def _resolve_node_entrypoint(manifest: Dict[str, Any], runtime_name: str, handler_name: str) -> str:
        for adapter in manifest.get("adapters", []):
            if adapter.get("runtime") == runtime_name:
                entrypoint = adapter.get("entrypoint")
                if not entrypoint:
                    continue
                module_name, attr = entrypoint.split(":", 1)
                return f"{module_name}:{attr}.{handler_name}"
        raise ValueError(f"Unable to resolve handler {handler_name} for runtime {runtime_name}")
