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
from scheduler_api.infra.catalog.hub_link import write_hub_link
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

def _validate_segment(value: str, label: str) -> None:
    if not value:
        raise HubMirrorError(f"{label} is required.")
    if Path(value).is_absolute():
        raise HubMirrorError(f"{label} is invalid.")
    if ".." in Path(value).parts:
        raise HubMirrorError(f"{label} is invalid.")



def _compose_hub_name(owner: str | None, name: str) -> str:
    if owner:
        return f"{owner}/{name}"
    return name


class HubMirrorService:
    def __init__(self) -> None:
        settings = get_api_settings()
        self._mirror_root = Path(settings.hub_mirror_root).expanduser().resolve()
        self._packages_root = Path(settings.packages_root).expanduser().resolve()
        self._index = PackageIndexService(
            packages_root=self._mirror_root,
            source="hub",
        )

    def ensure_package(
        self,
        *,
        name: str,
        version: str,
        owner: str | None = None,
    ) -> dict[str, object]:
        try:
            existing = self._index.get_package_detail(name, version, owner_id=owner)
            archive_path = self._mirror_root / str(existing.get("archivePath") or "")
            if archive_path.is_file():
                return existing
        except Exception:
            pass

        hub_name = _compose_hub_name(owner, name)
        try:
            client = HubClient.from_settings()
        except HubNotConfiguredError as exc:
            raise HubMirrorError(str(exc)) from exc
        try:
            version_detail = client.get_package_version(hub_name, version)
        except HubNotFoundError as exc:
            raise HubMirrorError("Package version not found in Hub.") from exc
        except HubClientError as exc:
            raise HubMirrorError(str(exc)) from exc

        expected_sha = version_detail.get("archiveSha256")
        owner_id = str(version_detail.get("ownerId") or owner or "hub")
        tmp_dir = Path(tempfile.mkdtemp(prefix="hub-pkg-"))
        archive_tmp = tmp_dir / PACKAGE_ARCHIVE_NAME
        try:
            try:
                client.download_package_archive(
                    hub_name,
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

            target_dir = self._mirror_root / owner_id / name / version
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

    def install_to_catalog(
        self,
        *,
        name: str,
        version: str,
        owner: str | None = None,
    ) -> None:
        detail = self._index.get_package_detail(name, version, owner_id=owner)
        archive_rel = detail.get("archivePath")
        archive_path = self._mirror_root / str(archive_rel)
        if not archive_path.is_file():
            raise HubMirrorError("Package archive missing from Hub mirror.")

        owner_id = str(owner or detail.get("ownerId") or "hub")
        target_dir = self._packages_root / owner_id / name / version
        if target_dir.exists():
            shutil.rmtree(target_dir)
        target_dir.mkdir(parents=True, exist_ok=True)
        _safe_extract_zip(archive_path, target_dir)
        hub_payload: dict[str, object] | None = None
        resolved_owner = owner or detail.get("ownerId")
        hub_name = _compose_hub_name(resolved_owner, name)
        try:
            hub_detail = HubClient.from_settings().get_package_version(hub_name, version)
        except (HubNotConfiguredError, HubClientError):
            hub_detail = None
        if isinstance(hub_detail, dict):
            resolved_owner = hub_detail.get("ownerId") or resolved_owner
            hub_name = _compose_hub_name(resolved_owner, name)
            hub_payload = {
                "hubName": hub_name,
                "hubVersion": version,
                "ownerId": hub_detail.get("ownerId"),
                "ownerName": hub_detail.get("ownerName"),
                "visibility": hub_detail.get("visibility"),
                "publishedAt": hub_detail.get("publishedAt"),
                "archiveSha256": hub_detail.get("archiveSha256"),
            }
        if hub_payload:
            write_hub_link(target_dir, hub_payload)
        catalog.reload()

    def uninstall_from_catalog(
        self,
        *,
        name: str,
        version: str | None = None,
        owner: str | None = None,
    ) -> list[str]:
        if owner is None:
            raise HubMirrorError("Package owner is required.")
        _validate_segment(owner, "Owner")
        _validate_segment(name, "Package name")
        if version:
            _validate_segment(version, "Version")

        target_base = self._packages_root / owner / name
        if not target_base.exists():
            raise HubMirrorError("Package is not installed.")

        removed_versions: list[str] = []
        try:
            if version:
                target_dir = target_base / version
                if not target_dir.exists():
                    raise HubMirrorError("Package version is not installed.")
                shutil.rmtree(target_dir)
                removed_versions.append(version)
            else:
                for version_dir in target_base.iterdir():
                    if not version_dir.is_dir():
                        continue
                    shutil.rmtree(version_dir)
                    removed_versions.append(version_dir.name)
        except HubMirrorError:
            raise
        except Exception as exc:
            raise HubMirrorError("Failed to uninstall package.") from exc

        try:
            if target_base.exists():
                next(target_base.iterdir())
        except StopIteration:
            target_base.rmdir()
        owner_dir = target_base.parent
        try:
            if owner_dir.exists():
                next(owner_dir.iterdir())
        except StopIteration:
            owner_dir.rmdir()

        catalog.reload()
        return removed_versions


hub_mirror_service = HubMirrorService()

__all__ = [
    "HubMirrorError",
    "HubMirrorService",
    "hub_mirror_service",
]
