from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from hub_api.db.models import HubPackage, HubPackagePermission, HubPackageVersion
from hub_api.db.session import SessionLocal
from hub_api.repo.common import _generate_id, _key, _now
from hub_api.storage import get_package_archive_path, package_archive_relative_path

DEFAULT_VISIBILITY = "public"

def _package_permission_from_model(permission: HubPackagePermission) -> dict[str, Any]:
    return {
        "id": permission.id,
        "packageName": permission.package_name,
        "subjectType": permission.subject_type,
        "subjectId": permission.subject_id,
        "role": permission.role,
        "createdAt": permission.created_at,
    }

def list_package_permissions(package_name: str) -> list[dict[str, Any]]:
    with SessionLocal() as session:
        perms = session.execute(
            select(HubPackagePermission).where(
                HubPackagePermission.package_name == package_name
            )
        ).scalars().all()
        return [_package_permission_from_model(perm) for perm in perms]

def add_package_permission(
    *,
    package_name: str,
    subject_type: str,
    subject_id: str,
    role: str,
) -> dict[str, Any]:
    with SessionLocal() as session:
        permission = session.execute(
            select(HubPackagePermission).where(
                HubPackagePermission.package_name == package_name,
                HubPackagePermission.subject_type == subject_type,
                HubPackagePermission.subject_id == subject_id,
            )
        ).scalar_one_or_none()
        if permission:
            permission.role = role
        else:
            permission = HubPackagePermission(
                id=_generate_id(),
                package_name=package_name,
                subject_type=subject_type,
                subject_id=subject_id,
                role=role,
                created_at=_now(),
            )
            session.add(permission)
        session.commit()
        session.refresh(permission)
        return _package_permission_from_model(permission)

def update_package_permission(permission_id: str, role: str) -> dict[str, Any]:
    with SessionLocal() as session:
        permission = session.get(HubPackagePermission, permission_id)
        if not permission:
            raise ValueError("permission_not_found")
        permission.role = role
        session.commit()
        session.refresh(permission)
        return _package_permission_from_model(permission)

def delete_package_permission(permission_id: str) -> None:
    with SessionLocal() as session:
        permission = session.get(HubPackagePermission, permission_id)
        if permission:
            session.delete(permission)
            session.commit()

def _package_record_from_model(
    package: HubPackage,
    *,
    include_versions: bool,
) -> dict[str, Any]:
    versions_map: dict[str, dict[str, Any]] = {}
    if include_versions:
        for version in package.versions:
            versions_map[version.version] = _package_version_record_from_model(
                package,
                version,
            )
    return {
        "name": package.name,
        "latestVersion": package.latest_version,
        "description": package.description,
        "tags": package.tags,
        "ownerId": package.owner_id,
        "ownerName": package.owner_name,
        "updatedAt": package.updated_at,
        "createdAt": package.created_at,
        "versions": versions_map,
        "distTags": dict(package.dist_tags or {}),
        "readme": package.readme,
        "visibility": package.visibility,
    }

def _package_version_record_from_model(
    package: HubPackage,
    version: HubPackageVersion,
) -> dict[str, Any]:
    return {
        "name": package.name,
        "version": version.version,
        "description": version.description,
        "readme": version.readme,
        "tags": version.tags,
        "distTags": dict(package.dist_tags or {}),
        "archiveSha256": version.archive_sha256,
        "archiveSizeBytes": version.archive_size_bytes,
        "ownerId": version.owner_id or package.owner_id,
        "ownerName": version.owner_name or package.owner_name,
        "visibility": version.visibility or package.visibility,
        "publishedAt": version.published_at,
        "updatedAt": version.updated_at,
        "archivePath": version.archive_path,
    }

def _load_package(
    session,
    name: str,
    *,
    include_versions: bool,
) -> HubPackage | None:
    stmt = select(HubPackage).where(HubPackage.name_normalized == _key(name))
    if include_versions:
        stmt = stmt.options(selectinload(HubPackage.versions))
    return session.execute(stmt).scalar_one_or_none()

def list_packages() -> list[dict[str, Any]]:
    with SessionLocal() as session:
        packages = session.execute(select(HubPackage)).scalars().all()
        return [
            _package_record_from_model(package, include_versions=False)
            for package in packages
        ]

def get_package_record(name: str) -> dict[str, Any] | None:
    with SessionLocal() as session:
        package = _load_package(session, name, include_versions=True)
        if not package:
            return None
        return _package_record_from_model(package, include_versions=True)

def get_package_version_record(name: str, version: str) -> dict[str, Any] | None:
    with SessionLocal() as session:
        package = _load_package(session, name, include_versions=False)
        if not package:
            return None
        stmt = select(HubPackageVersion).where(
            HubPackageVersion.package_name == package.name,
            HubPackageVersion.version == version,
        )
        version_model = session.execute(stmt).scalar_one_or_none()
        if not version_model:
            return None
        return _package_version_record_from_model(package, version_model)

def reserve_package_record(
    *,
    name: str,
    owner_id: str,
    owner_name: str,
    visibility: str,
) -> dict[str, Any]:
    normalized = _key(name)
    with SessionLocal() as session:
        package = _load_package(session, name, include_versions=True)
        if package:
            return _package_record_from_model(package, include_versions=True)
        now = _now()
        package = HubPackage(
            name=name,
            name_normalized=normalized,
            description=None,
            tags=None,
            owner_id=owner_id,
            owner_name=owner_name,
            updated_at=now,
            created_at=now,
            dist_tags={},
            readme=None,
            visibility=visibility,
            latest_version=None,
        )
        session.add(package)
        session.commit()
        add_package_permission(
            package_name=name,
            subject_type="user",
            subject_id=owner_id,
            role="owner",
        )
        session.refresh(package)
        return _package_record_from_model(package, include_versions=True)

def publish_package_version(
    *,
    name: str,
    version: str,
    description: str | None,
    readme: str | None,
    tags: list[str] | None,
    visibility: str,
    owner_id: str,
    owner_name: str,
    publisher_id: str,
    archive_bytes: bytes | None,
    archive_sha256: str | None,
    archive_size_bytes: int | None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    normalized = _key(name)
    archive_relative = None
    archive_path = None
    created = False
    if archive_bytes is not None:
        archive_relative = package_archive_relative_path(name, version)
        archive_path = get_package_archive_path(name, version)
        archive_path.write_bytes(archive_bytes)

    try:
        with SessionLocal() as session:
            package = session.execute(
                select(HubPackage).where(HubPackage.name_normalized == normalized)
            ).scalar_one_or_none()
            if package and package.owner_id != owner_id:
                raise ValueError("package_owner_mismatch")
            if package is None:
                now = _now()
                package = HubPackage(
                    name=name,
                    name_normalized=normalized,
                    description=description,
                    readme=readme,
                    tags=tags,
                    owner_id=owner_id,
                    owner_name=owner_name,
                    updated_at=now,
                    created_at=now,
                    dist_tags={},
                    visibility=visibility,
                    latest_version=None,
                )
                session.add(package)
                session.flush()
                created = True

            existing_version = session.execute(
                select(HubPackageVersion).where(
                    HubPackageVersion.package_name == package.name,
                    HubPackageVersion.version == version,
                )
            ).scalar_one_or_none()
            if existing_version:
                raise ValueError("package_version_exists")

            now = _now()
            if description:
                package.description = description
            if readme:
                package.readme = readme
            if tags is not None:
                package.tags = tags
            package.visibility = visibility
            package.updated_at = now
            dist_tags = dict(package.dist_tags or {})
            dist_tags["latest"] = version
            package.dist_tags = dist_tags
            package.latest_version = version

            version_record = HubPackageVersion(
                package_name=package.name,
                version=version,
                description=description or package.description,
                readme=readme or package.readme,
                tags=tags if tags is not None else package.tags,
                archive_sha256=archive_sha256,
                archive_size_bytes=archive_size_bytes,
                archive_path=archive_relative,
                owner_id=owner_id,
                owner_name=owner_name,
                visibility=visibility,
                published_at=now,
                updated_at=now,
            )
            session.add(version_record)
            session.commit()
            session.refresh(package)
            session.refresh(version_record)
            record = _package_record_from_model(package, include_versions=True)
            version_payload = _package_version_record_from_model(package, version_record)
    except Exception:
        if archive_path and archive_path.exists():
            archive_path.unlink()
        raise

    if created:
        add_package_permission(
            package_name=name,
            subject_type="user",
            subject_id=owner_id,
            role="owner",
        )
    return record, version_payload

def set_package_tag_record(name: str, tag: str, version: str) -> dict[str, Any]:
    with SessionLocal() as session:
        package = _load_package(session, name, include_versions=True)
        if not package:
            raise ValueError("package_not_found")
        version_exists = any(item.version == version for item in package.versions)
        if not version_exists:
            raise ValueError("package_version_not_found")
        dist_tags = dict(package.dist_tags or {})
        dist_tags[tag] = version
        package.dist_tags = dist_tags
        now = _now()
        package.updated_at = now
        if tag == "latest":
            package.latest_version = version
        for version_record in package.versions:
            version_record.updated_at = now
        session.commit()
        session.refresh(package)
        return _package_record_from_model(package, include_versions=True)

def delete_package_tag_record(name: str, tag: str) -> dict[str, Any]:
    with SessionLocal() as session:
        package = _load_package(session, name, include_versions=True)
        if not package:
            raise ValueError("package_not_found")
        dist_tags = dict(package.dist_tags or {})
        if tag not in dist_tags:
            raise ValueError("package_tag_not_found")
        del dist_tags[tag]
        package.dist_tags = dist_tags
        now = _now()
        package.updated_at = now
        if tag == "latest":
            remaining = [version.version for version in package.versions]
            package.latest_version = remaining[0] if remaining else None
        for version_record in package.versions:
            version_record.updated_at = now
        session.commit()
        session.refresh(package)
        return _package_record_from_model(package, include_versions=True)

def update_package_visibility_record(name: str, visibility: str) -> dict[str, Any]:
    with SessionLocal() as session:
        package = _load_package(session, name, include_versions=True)
        if not package:
            raise ValueError("package_not_found")
        now = _now()
        package.visibility = visibility
        package.updated_at = now
        for version_record in package.versions:
            version_record.visibility = visibility
            version_record.updated_at = now
        session.commit()
        session.refresh(package)
        return _package_record_from_model(package, include_versions=True)

def transfer_package_record(
    name: str,
    new_owner_id: str,
    new_owner_name: str,
) -> dict[str, Any]:
    with SessionLocal() as session:
        package = _load_package(session, name, include_versions=True)
        if not package:
            raise ValueError("package_not_found")
        now = _now()
        package.owner_id = new_owner_id
        package.owner_name = new_owner_name
        package.updated_at = now
        for version_record in package.versions:
            version_record.owner_id = new_owner_id
            version_record.owner_name = new_owner_name
            version_record.updated_at = now
        session.commit()
        session.refresh(package)
        return _package_record_from_model(package, include_versions=True)
