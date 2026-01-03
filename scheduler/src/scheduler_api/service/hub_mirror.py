"""Mirror Hub packages into a local cache and catalog."""

from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import zipfile
from pathlib import Path

from scheduler_api.config.settings import get_api_settings
from scheduler_api.infra.catalog import catalog
from scheduler_api.service.hub_client import (
    HubClient,
    HubClientError,
    HubNotConfiguredError,
    HubNotFoundError,
)
from scheduler_api.service.package_index import PACKAGE_ARCHIVE_NAME, PackageIndexService
from shared.models.manifest import PackageManifest


class HubMirrorError(Exception):
    """Raised when Hub mirroring fails."""


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
                raise HubMirrorError("Archive contains invalid paths.")
        if "manifest.json" not in names:
            raise HubMirrorError("manifest.json must exist at the archive root.")
        with zip_file.open("manifest.json") as handle:
            return json.load(handle)


def _safe_extract_zip(archive_path: Path, target_dir: Path) -> None:
    with zipfile.ZipFile(archive_path) as zip_file:
        for info in zip_file.infolist():
            if info.is_dir():
                continue
            if _is_unsafe_entry(info.filename):
                raise HubMirrorError("Archive contains invalid paths.")
        zip_file.extractall(target_dir)


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class HubMirrorService:
    def __init__(self) -> None:
        settings = get_api_settings()
        self._mirror_root = Path(settings.hub_mirror_root).expanduser().resolve()
        self._packages_root = Path(settings.packages_root).expanduser().resolve()
        self._index = PackageIndexService(
            packages_root=self._mirror_root,
            source="hub",
        )

    def ensure_package(self, *, name: str, version: str) -> dict[str, object]:
        try:
            existing = self._index.get_package_detail(name, version)
            archive_path = self._mirror_root / str(existing.get("archivePath") or "")
            if archive_path.is_file():
                return existing
        except Exception:
            pass

        try:
            client = HubClient.from_settings()
        except HubNotConfiguredError as exc:
            raise HubMirrorError(str(exc)) from exc
        try:
            version_detail = client.get_package_version(name, version)
        except HubNotFoundError as exc:
            raise HubMirrorError("Package version not found in Hub.") from exc
        except HubClientError as exc:
            raise HubMirrorError(str(exc)) from exc

        expected_sha = version_detail.get("archiveSha256")
        owner_id = version_detail.get("ownerId") or "hub"
        tmp_dir = Path(tempfile.mkdtemp(prefix="hub-pkg-"))
        archive_tmp = tmp_dir / PACKAGE_ARCHIVE_NAME
        try:
            try:
                client.download_package_archive(
                    name,
                    version=version,
                    dest_path=archive_tmp,
                )
            except HubClientError as exc:
                raise HubMirrorError(str(exc)) from exc
            manifest_payload = _read_manifest_from_zip(archive_tmp)
            manifest_model = PackageManifest.model_validate(manifest_payload)
            if manifest_model.name != name or manifest_model.version != version:
                raise HubMirrorError("Manifest name/version mismatch.")

            if expected_sha:
                actual_sha = _hash_file(archive_tmp)
                if actual_sha != expected_sha:
                    raise HubMirrorError("Package archive checksum mismatch.")

            target_dir = self._mirror_root / name / version
            target_dir.mkdir(parents=True, exist_ok=True)
            archive_path = target_dir / PACKAGE_ARCHIVE_NAME
            shutil.copyfile(archive_tmp, archive_path)
            return self._index.register_package(
                manifest_model,
                archive_path,
                owner_id=str(owner_id),
            )
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def install_to_catalog(self, *, name: str, version: str) -> None:
        detail = self._index.get_package_detail(name, version)
        archive_rel = detail.get("archivePath")
        archive_path = self._mirror_root / str(archive_rel)
        if not archive_path.is_file():
            raise HubMirrorError("Package archive missing from Hub mirror.")

        target_dir = self._packages_root / name / version
        if target_dir.exists():
            shutil.rmtree(target_dir)
        target_dir.mkdir(parents=True, exist_ok=True)
        _safe_extract_zip(archive_path, target_dir)
        catalog.reload()


hub_mirror_service = HubMirrorService()

__all__ = [
    "HubMirrorError",
    "HubMirrorService",
    "hub_mirror_service",
]
