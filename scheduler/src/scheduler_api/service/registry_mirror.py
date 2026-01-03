"""Mirror registry packages into a local cache and catalog."""

from __future__ import annotations

import json
import shutil
import tempfile
import zipfile
from pathlib import Path

from scheduler_api.config.settings import get_api_settings
from scheduler_api.infra.catalog import catalog
from scheduler_api.service.package_index import PACKAGE_ARCHIVE_NAME, PackageIndexService
from scheduler_api.service.registry_client import RegistryActor, RegistryClient
from shared.models.manifest import PackageManifest


class RegistryMirrorError(Exception):
    """Raised when registry mirroring fails."""


def _is_unsafe_entry(entry_name: str) -> bool:
    entry_path = Path(entry_name)
    if entry_path.is_absolute():
        return True
    return ".." in entry_path.parts


def _read_manifest_from_zip(archive_path: Path) -> dict:
    with zipfile.ZipFile(archive_path) as zip_file:
        names = {info.filename for info in zip_file.infolist() if not info.is_dir()}
        for name in names:
            if _is_unsafe_entry(name):
                raise RegistryMirrorError("Archive contains invalid paths.")
        if "manifest.json" not in names:
            raise RegistryMirrorError("manifest.json must exist at the archive root.")
        with zip_file.open("manifest.json") as handle:
            return json.load(handle)


def _safe_extract_zip(archive_path: Path, target_dir: Path) -> None:
    with zipfile.ZipFile(archive_path) as zip_file:
        for info in zip_file.infolist():
            if info.is_dir():
                continue
            if _is_unsafe_entry(info.filename):
                raise RegistryMirrorError("Archive contains invalid paths.")
        zip_file.extractall(target_dir)


class RegistryMirrorService:
    def __init__(self) -> None:
        settings = get_api_settings()
        self._mirror_root = Path(settings.registry_mirror_root).expanduser().resolve()
        self._packages_root = Path(settings.packages_root).expanduser().resolve()
        self._index = PackageIndexService(
            packages_root=self._mirror_root,
            source="registry",
        )

    def ensure_package(
        self,
        *,
        name: str,
        version: str,
        actor: RegistryActor | None,
    ) -> dict[str, object]:
        try:
            existing = self._index.get_package_detail(name, version)
            archive_path = self._mirror_root / str(existing.get("archivePath") or "")
            if archive_path.is_file():
                return existing
        except Exception:
            pass

        client = RegistryClient.from_settings()
        tmp_dir = Path(tempfile.mkdtemp(prefix="registry-pkg-"))
        archive_tmp = tmp_dir / PACKAGE_ARCHIVE_NAME
        try:
            try:
                client.download_package_archive(
                    name,
                    version=version,
                    dest_path=archive_tmp,
                    actor=actor,
                )
            except Exception as exc:
                raise RegistryMirrorError(str(exc)) from exc
            manifest_payload = _read_manifest_from_zip(archive_tmp)
            manifest_model = PackageManifest.model_validate(manifest_payload)
            if manifest_model.name != name or manifest_model.version != version:
                raise RegistryMirrorError("Manifest name/version mismatch.")

            target_dir = self._mirror_root / name / version
            target_dir.mkdir(parents=True, exist_ok=True)
            archive_path = target_dir / PACKAGE_ARCHIVE_NAME
            shutil.copyfile(archive_tmp, archive_path)
            owner_id = "registry"
            if actor:
                owner_id = actor.registry_user_id or actor.platform_user_id or owner_id
            return self._index.register_package(
                manifest_model,
                archive_path,
                owner_id=owner_id,
            )
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def install_to_catalog(self, *, name: str, version: str) -> None:
        detail = self._index.get_package_detail(name, version)
        archive_rel = detail.get("archivePath")
        archive_path = self._mirror_root / str(archive_rel)
        if not archive_path.is_file():
            raise RegistryMirrorError("Package archive missing from registry mirror.")

        target_dir = self._packages_root / name / version
        if target_dir.exists():
            shutil.rmtree(target_dir)
        target_dir.mkdir(parents=True, exist_ok=True)
        _safe_extract_zip(archive_path, target_dir)
        catalog.reload()


registry_mirror_service = RegistryMirrorService()

__all__ = [
    "RegistryMirrorError",
    "RegistryMirrorService",
    "registry_mirror_service",
]
