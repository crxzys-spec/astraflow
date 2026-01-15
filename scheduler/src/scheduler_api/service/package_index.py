"""Service for indexing local package manifests."""

from __future__ import annotations

import hashlib
import json
import logging
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from sqlalchemy.orm import Session

from scheduler_api.config.settings import get_api_settings
from scheduler_api.db.models import PackageDistTagRecord, PackageIndexRecord
from scheduler_api.db.session import run_in_session
from scheduler_api.infra.catalog import LOCAL_OWNER
from scheduler_api.infra.catalog.package_catalog import _version_key
from scheduler_api.repo.package_dist_tags import PackageDistTagRepository
from scheduler_api.repo.package_index import PackageIndexRepository
from shared.models.manifest import PackageManifest

LOGGER = logging.getLogger(__name__)
PACKAGE_ARCHIVE_NAME = "package.zip"
PACKAGE_STATUS_ACTIVE = "active"
PACKAGE_STATUS_DEPRECATED = "deprecated"
PACKAGE_STATUS_YANKED = "yanked"
PACKAGE_STATUS_VALUES = {
    PACKAGE_STATUS_ACTIVE,
    PACKAGE_STATUS_DEPRECATED,
    PACKAGE_STATUS_YANKED,
}


class PackageIndexError(Exception):
    """Base error for package index lookups."""


class PublishedPackageNotFoundError(PackageIndexError):
    """Raised when a published package name is unknown."""


class PublishedPackageVersionNotFoundError(PackageIndexError):
    """Raised when a published package version is unavailable."""


class PublishedPackageAlreadyExistsError(PackageIndexError):
    """Raised when a published package name/version already exists."""


class PublishedPackageOwnershipError(PackageIndexError):
    """Raised when a publisher attempts to publish a package they do not own."""


class PublishedPackageStatusError(PackageIndexError):
    """Raised when an invalid package status is provided."""


class PublishedPackageTagNotFoundError(PackageIndexError):
    """Raised when a dist-tag is missing."""


class PublishedPackageQuotaError(PackageIndexError):
    """Raised when package storage quota would be exceeded."""


@dataclass(frozen=True)
class PackageGcItem:
    owner_id: str
    name: str
    version: str
    size_bytes: int | None
    archive_path: str | None

    def to_dict(self) -> dict[str, object]:
        return {
            "ownerId": self.owner_id,
            "name": self.name,
            "version": self.version,
            "sizeBytes": self.size_bytes,
            "archivePath": self.archive_path,
        }


def _serialize_manifest(manifest: PackageManifest) -> str:
    payload = manifest.model_dump(by_alias=True, exclude_none=True, mode="json")
    return json.dumps(payload, ensure_ascii=True, sort_keys=True)


def _hash_manifest(manifest_json: str) -> str:
    return hashlib.sha256(manifest_json.encode("utf-8")).hexdigest()


def _resolve_localized_text(value: object | None, fallback: str) -> str:
    if hasattr(value, "root"):
        value = value.root
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        normalized = {
            str(key).lower().replace("_", "-"): entry
            for key, entry in value.items()
            if isinstance(entry, str)
        }
        default_entry = normalized.get("default")
        if default_entry:
            return default_entry
        for candidate in ("en-us", "en", "zh-cn", "zh", "ja", "ko"):
            entry = normalized.get(candidate)
            if entry:
                return entry
        for key in sorted(normalized.keys()):
            entry = normalized.get(key)
            if entry:
                return entry
    return fallback


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _normalize_owner_id(owner_id: str | None) -> str:
    return owner_id or LOCAL_OWNER


def _resolve_owner_id(records: Iterable[PackageIndexRecord], owner_id: str | None) -> str:
    owners = {_normalize_owner_id(record.owner_id) for record in records}
    if not owners:
        return _normalize_owner_id(owner_id)
    if owner_id:
        if owner_id not in owners:
            raise PublishedPackageNotFoundError(
                f"Package owner '{owner_id}' not found."
            )
        return owner_id
    if LOCAL_OWNER in owners:
        return LOCAL_OWNER
    if len(owners) == 1:
        return owners.pop()
    raise PublishedPackageOwnershipError("Package owner is required.")


def _resolve_owner(records: Iterable[PackageIndexRecord], owner_id: str) -> None:
    owners = {_normalize_owner_id(record.owner_id) for record in records}
    if not owners:
        return
    if len(owners) > 1:
        raise PublishedPackageOwnershipError(
            "Package ownership is inconsistent; contact an administrator."
        )
    if owner_id not in owners:
        raise PublishedPackageOwnershipError(
            "Only the publisher can publish new versions for this package."
        )


def _resolve_archive_path(record: PackageIndexRecord, packages_root: Path) -> Path:
    if record.archive_path:
        return packages_root / record.archive_path
    owner_id = _normalize_owner_id(record.owner_id)
    return packages_root / owner_id / record.name / record.version / PACKAGE_ARCHIVE_NAME


def _resolve_archive_size(
    record: PackageIndexRecord,
    packages_root: Path,
    session: Session,
) -> int | None:
    if record.archive_size_bytes is not None:
        return record.archive_size_bytes
    path = _resolve_archive_path(record, packages_root)
    if not path.is_file():
        return None
    size_bytes = path.stat().st_size
    record.archive_size_bytes = size_bytes
    session.add(record)
    return size_bytes


def _sum_archive_sizes(
    records: Iterable[PackageIndexRecord],
    packages_root: Path,
    session: Session,
) -> int:
    total = 0
    for record in records:
        size_bytes = _resolve_archive_size(record, packages_root, session)
        if size_bytes:
            total += size_bytes
    return total


def _cleanup_archive_path(path: Path) -> None:
    try:
        if path.is_file():
            path.unlink()
        version_dir = path.parent
        if version_dir.is_dir():
            shutil.rmtree(version_dir, ignore_errors=True)
        package_dir = version_dir.parent
        if package_dir.is_dir():
            try:
                next(package_dir.iterdir())
            except StopIteration:
                package_dir.rmdir()
    except Exception:
        LOGGER.warning("Failed to cleanup archive path %s", path, exc_info=True)


class PackageIndexService:
    def __init__(
        self,
        *,
        packages_root: Path | None = None,
        source: str = "published",
    ) -> None:
        settings = get_api_settings()
        self._packages_root = Path(
            packages_root or settings.published_packages_root
        ).expanduser().resolve()
        self._source = source
        self._repo = PackageIndexRepository()
        self._tag_repo = PackageDistTagRepository()

    def list_packages(self) -> list[dict[str, object]]:
        def _list(session: Session) -> list[dict[str, object]]:
            records = self._repo.list_by_source(source=self._source, session=session)
            tag_records = self._tag_repo.list_by_source(source=self._source, session=session)
            tags_by_name: dict[tuple[str, str], dict[str, str]] = {}
            for tag_record in tag_records:
                owner_id = _normalize_owner_id(tag_record.owner_id)
                tags_by_name.setdefault((owner_id, tag_record.name), {})[
                    tag_record.tag
                ] = tag_record.version
            grouped: dict[tuple[str, str], list[PackageIndexRecord]] = {}
            for record in records:
                owner_id = _normalize_owner_id(record.owner_id)
                grouped.setdefault((owner_id, record.name), []).append(record)

            summaries: list[dict[str, object]] = []
            for (owner_id, name), items in grouped.items():
                versions = sorted((item.version for item in items), key=_version_key, reverse=True)
                latest = max(items, key=lambda item: _version_key(item.version))
                dist_tags = tags_by_name.get((owner_id, name), {})
                default_version = dist_tags.get("latest") or (versions[0] if versions else None)
                summaries.append(
                    {
                        "name": name,
                        "description": latest.description,
                        "latestVersion": versions[0] if versions else None,
                        "defaultVersion": default_version,
                        "versions": versions,
                        "ownerId": owner_id,
                        "distTags": dist_tags,
                    }
                )
            summaries.sort(key=lambda item: (item.get("name"), item.get("ownerId")))
            return summaries

        return run_in_session(_list)

    def get_package_detail(
        self,
        name: str,
        version: str | None = None,
        *,
        owner_id: str | None = None,
    ) -> dict[str, object]:
        def _get(session: Session) -> dict[str, object]:
            records = self._repo.list_by_name(name=name, source=self._source, session=session)
            if not records:
                raise PublishedPackageNotFoundError(f"Package '{name}' not found")
            resolved_owner = _resolve_owner_id(records, owner_id)
            owner_records = [
                record
                for record in records
                if _normalize_owner_id(record.owner_id) == resolved_owner
            ]
            versions = sorted(
                (record.version for record in owner_records),
                key=_version_key,
                reverse=True,
            )
            tag_records = self._tag_repo.list_by_name(
                name=name,
                source=self._source,
                session=session,
                owner_id=resolved_owner,
            )
            dist_tags = {record.tag: record.version for record in tag_records}
            target_version = version or dist_tags.get("latest") or versions[0]
            record = next((item for item in owner_records if item.version == target_version), None)
            if record is None:
                raise PublishedPackageVersionNotFoundError(
                    f"Package '{name}' has no version '{target_version}'"
                )
            archive_size = _resolve_archive_size(record, self._packages_root, session)
            return {
                "name": name,
                "ownerId": resolved_owner,
                "version": target_version,
                "availableVersions": versions,
                "manifest": json.loads(record.manifest_json),
                "archiveSha256": record.archive_sha256,
                "archiveSizeBytes": archive_size,
                "archivePath": record.archive_path,
                "status": record.status,
                "distTags": dist_tags,
            }

        return run_in_session(_get)

    def register_package(
        self,
        manifest: PackageManifest,
        archive_path: Path,
        *,
        owner_id: str,
    ) -> dict[str, object]:
        manifest_json = _serialize_manifest(manifest)
        manifest_hash = _hash_manifest(manifest_json)
        archive_sha256 = _hash_file(archive_path)
        archive_size_bytes = archive_path.stat().st_size
        archive_rel_path = str(
            Path(owner_id) / manifest.name / manifest.version / PACKAGE_ARCHIVE_NAME
        )
        now = datetime.now(timezone.utc)

        def _register(session: Session) -> None:
            existing_versions = self._repo.list_by_name(
                name=manifest.name,
                source=self._source,
                session=session,
            )
            if existing_versions:
                legacy_records = [record for record in existing_versions if record.owner_id is None]
                owner_records = [
                    record
                    for record in existing_versions
                    if _normalize_owner_id(record.owner_id) == owner_id
                ]
                if legacy_records and not owner_records:
                    for record in legacy_records:
                        record.owner_id = owner_id
                        session.add(record)
                    owner_records = legacy_records
                if owner_records:
                    _resolve_owner(owner_records, owner_id)

            existing = self._repo.get_by_name_version(
                name=manifest.name,
                version=manifest.version,
                source=self._source,
                session=session,
                owner_id=owner_id,
            )
            if existing:
                raise PublishedPackageAlreadyExistsError(
                    f"Package '{manifest.name}' version '{manifest.version}' already exists."
                )
            session.add(
                PackageIndexRecord(
                    name=manifest.name,
                    version=manifest.version,
                    source=self._source,
                    schema_version=manifest.schemaVersion,
                    description=_resolve_localized_text(
                        manifest.description, manifest.name
                    ),
                    manifest_json=manifest_json,
                    manifest_hash=manifest_hash,
                    archive_path=archive_rel_path,
                    archive_sha256=archive_sha256,
                    archive_size_bytes=archive_size_bytes,
                    owner_id=owner_id,
                    status=PACKAGE_STATUS_ACTIVE,
                    created_at=now,
                    updated_at=now,
                    last_seen_at=now,
                )
            )
            tag_record = self._tag_repo.get_by_name_tag(
                name=manifest.name,
                tag="latest",
                source=self._source,
                session=session,
                owner_id=owner_id,
            )
            if tag_record:
                tag_record.version = manifest.version
                tag_record.updated_at = now
                session.add(tag_record)
            else:
                session.add(
                    PackageDistTagRecord(
                        owner_id=owner_id,
                        name=manifest.name,
                        tag="latest",
                        source=self._source,
                        version=manifest.version,
                        created_at=now,
                        updated_at=now,
                    )
                )

        run_in_session(_register)
        return self.get_package_detail(manifest.name, manifest.version, owner_id=owner_id)

    def ensure_storage_quota(
        self,
        *,
        owner_id: str,
        name: str,
        incoming_bytes: int,
    ) -> None:
        settings = get_api_settings()
        owner_limit = int(settings.published_packages_max_owner_bytes)
        package_limit = int(settings.published_packages_max_package_bytes)
        if owner_limit <= 0 and package_limit <= 0:
            return

        def _check(session: Session) -> None:
            if owner_limit > 0:
                owner_records = self._repo.list_by_owner(
                    owner_id=owner_id,
                    source=self._source,
                    session=session,
                )
                owner_bytes = _sum_archive_sizes(owner_records, self._packages_root, session)
                if owner_bytes + incoming_bytes > owner_limit:
                    raise PublishedPackageQuotaError("Owner storage quota exceeded.")
            if package_limit > 0:
                package_records = self._repo.list_by_owner_name(
                    owner_id=owner_id,
                    name=name,
                    source=self._source,
                    session=session,
                )
                package_bytes = _sum_archive_sizes(package_records, self._packages_root, session)
                if package_bytes + incoming_bytes > package_limit:
                    raise PublishedPackageQuotaError("Package storage quota exceeded.")

        run_in_session(_check)

    def set_package_status(
        self,
        name: str,
        version: str,
        status: str,
        *,
        owner_id: str,
    ) -> dict[str, object]:
        if status not in PACKAGE_STATUS_VALUES:
            raise PublishedPackageStatusError("Invalid package status.")
        now = datetime.now(timezone.utc)

        def _set(session: Session) -> None:
            records = self._repo.list_by_owner_name(
                owner_id=owner_id,
                name=name,
                source=self._source,
                session=session,
            )
            if not records:
                raise PublishedPackageNotFoundError(f"Package '{name}' not found")
            _resolve_owner(records, owner_id)
            record = next((item for item in records if item.version == version), None)
            if record is None:
                raise PublishedPackageVersionNotFoundError(
                    f"Package '{name}' has no version '{version}'"
                )
            record.status = status
            record.updated_at = now
            session.add(record)

        run_in_session(_set)
        return self.get_package_detail(name, version, owner_id=owner_id)

    def set_dist_tag(
        self,
        name: str,
        tag: str,
        version: str,
        *,
        owner_id: str,
    ) -> None:
        now = datetime.now(timezone.utc)

        def _set(session: Session) -> None:
            records = self._repo.list_by_owner_name(
                owner_id=owner_id,
                name=name,
                source=self._source,
                session=session,
            )
            if not records:
                raise PublishedPackageNotFoundError(f"Package '{name}' not found")
            _resolve_owner(records, owner_id)
            existing_version = self._repo.get_by_name_version(
                name=name,
                version=version,
                source=self._source,
                session=session,
                owner_id=owner_id,
            )
            if existing_version is None:
                raise PublishedPackageVersionNotFoundError(
                    f"Package '{name}' has no version '{version}'"
                )
            tag_record = self._tag_repo.get_by_name_tag(
                name=name,
                tag=tag,
                source=self._source,
                session=session,
                owner_id=owner_id,
            )
            if tag_record:
                tag_record.version = version
                tag_record.updated_at = now
                session.add(tag_record)
            else:
                session.add(
                    PackageDistTagRecord(
                        owner_id=owner_id,
                        name=name,
                        tag=tag,
                        source=self._source,
                        version=version,
                        created_at=now,
                        updated_at=now,
                    )
                )

        run_in_session(_set)

    def delete_dist_tag(
        self,
        name: str,
        tag: str,
        *,
        owner_id: str,
    ) -> None:
        def _delete(session: Session) -> None:
            records = self._repo.list_by_owner_name(
                owner_id=owner_id,
                name=name,
                source=self._source,
                session=session,
            )
            if not records:
                raise PublishedPackageNotFoundError(f"Package '{name}' not found")
            _resolve_owner(records, owner_id)
            tag_record = self._tag_repo.get_by_name_tag(
                name=name,
                tag=tag,
                source=self._source,
                session=session,
                owner_id=owner_id,
            )
            if tag_record is None:
                raise PublishedPackageTagNotFoundError(
                    f"Package '{name}' has no tag '{tag}'"
                )
            session.delete(tag_record)

        run_in_session(_delete)

    def get_archive_path(
        self,
        name: str,
        version: str | None = None,
        *,
        owner_id: str | None = None,
    ) -> tuple[Path, str | None, str]:
        detail = self.get_package_detail(name, version, owner_id=owner_id)
        archive_path = detail.get("archivePath")
        resolved_version = str(detail.get("version") or "")
        resolved_owner = str(detail.get("ownerId") or owner_id or LOCAL_OWNER)
        if archive_path:
            path = self._packages_root / archive_path
        else:
            path = self._packages_root / resolved_owner / name / resolved_version / PACKAGE_ARCHIVE_NAME
        return path, detail.get("archiveSha256"), resolved_version

    def gc_packages(
        self,
        *,
        package_name: str | None,
        max_versions: int | None,
        dry_run: bool,
        owner_id: str | None = None,
    ) -> tuple[list[PackageGcItem], int]:
        settings = get_api_settings()
        limit = int(settings.published_packages_max_versions_per_package)
        if max_versions is not None:
            limit = int(max_versions)
        if limit <= 0:
            return [], 0

        def _gc(session: Session) -> tuple[list[PackageGcItem], int, list[Path]]:
            if package_name:
                records = self._repo.list_by_name(
                    name=package_name,
                    source=self._source,
                    session=session,
                    owner_id=owner_id,
                )
            elif owner_id:
                records = self._repo.list_by_owner(
                    owner_id=owner_id,
                    source=self._source,
                    session=session,
                )
            else:
                records = self._repo.list_by_source(source=self._source, session=session)

            grouped: dict[tuple[str, str], list[PackageIndexRecord]] = {}
            for record in records:
                resolved_owner = _normalize_owner_id(record.owner_id)
                grouped.setdefault((resolved_owner, record.name), []).append(record)

            removed: list[PackageGcItem] = []
            removed_paths: list[Path] = []
            total_bytes = 0
            now = datetime.now(timezone.utc)

            for (resolved_owner, name), items in grouped.items():
                versions_sorted = sorted(items, key=lambda item: _version_key(item.version), reverse=True)
                tag_records = self._tag_repo.list_by_name(
                    name=name,
                    source=self._source,
                    session=session,
                    owner_id=resolved_owner,
                )
                tagged_versions = {record.version for record in tag_records}
                keep_versions = {record.version for record in versions_sorted[:limit]}
                keep_versions.update(tagged_versions)
                remove_records = [record for record in items if record.version not in keep_versions]
                if not remove_records:
                    continue

                remove_versions = {record.version for record in remove_records}
                for record in remove_records:
                    size_bytes = _resolve_archive_size(record, self._packages_root, session)
                    total_bytes += size_bytes or 0
                    removed.append(
                        PackageGcItem(
                            owner_id=resolved_owner,
                            name=record.name,
                            version=record.version,
                            size_bytes=size_bytes,
                            archive_path=record.archive_path,
                        )
                    )
                    removed_paths.append(_resolve_archive_path(record, self._packages_root))
                    if not dry_run:
                        session.delete(record)

                if not dry_run:
                    for tag_record in tag_records:
                        if tag_record.version in remove_versions:
                            session.delete(tag_record)

                    remaining_versions = [
                        record.version for record in items if record.version not in remove_versions
                    ]
                    if remaining_versions:
                        latest_version = max(remaining_versions, key=_version_key)
                        latest_tag = next(
                            (record for record in tag_records if record.tag == "latest"),
                            None,
                        )
                        if latest_tag:
                            latest_tag.version = latest_version
                            latest_tag.updated_at = now
                            session.add(latest_tag)
                        else:
                            session.add(
                                PackageDistTagRecord(
                                    owner_id=resolved_owner,
                                    name=name,
                                    tag="latest",
                                    source=self._source,
                                    version=latest_version,
                                    created_at=now,
                                    updated_at=now,
                                )
                            )

            return removed, total_bytes, removed_paths

        removed, total_bytes, removed_paths = run_in_session(_gc)
        if not dry_run:
            for path in removed_paths:
                _cleanup_archive_path(path)
        return removed, total_bytes


package_index_service = PackageIndexService()

__all__ = [
    "PackageIndexService",
    "PackageIndexError",
    "PublishedPackageAlreadyExistsError",
    "PublishedPackageOwnershipError",
    "PublishedPackageNotFoundError",
    "PublishedPackageStatusError",
    "PublishedPackageTagNotFoundError",
    "PublishedPackageVersionNotFoundError",
    "PublishedPackageQuotaError",
    "PACKAGE_STATUS_VALUES",
    "PACKAGE_ARCHIVE_NAME",
    "package_index_service",
]
