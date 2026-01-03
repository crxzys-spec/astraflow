from __future__ import annotations

import json
import shutil
import tempfile
import zipfile
from pathlib import Path

from fastapi import HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse

from scheduler_api.audit import record_audit_event
from scheduler_api.apis.published_packages_api_base import BasePublishedPackagesApi
from scheduler_api.auth.roles import WORKFLOW_EDIT_ROLES, WORKFLOW_VIEW_ROLES, require_roles
from scheduler_api.config.settings import get_api_settings
from scheduler_api.http.errors import bad_request, conflict, forbidden, not_found
from scheduler_api.models.package_detail import PackageDetail
from scheduler_api.models.package_list import PackageList
from scheduler_api.models.package_manifest import PackageManifest as ApiPackageManifest
from scheduler_api.models.package_summary import PackageSummary
from scheduler_api.models.published_package_gc_item import PublishedPackageGcItem
from scheduler_api.models.published_package_gc_request import PublishedPackageGcRequest
from scheduler_api.models.published_package_gc_result import PublishedPackageGcResult
from scheduler_api.models.published_package_registry import PublishedPackageRegistry
from scheduler_api.models.published_package_reserve_request import PublishedPackageReserveRequest
from scheduler_api.models.published_package_status_request import PublishedPackageStatusRequest
from scheduler_api.models.published_package_tag_request import PublishedPackageTagRequest
from scheduler_api.models.published_package_transfer_request import PublishedPackageTransferRequest
from scheduler_api.models.published_package_visibility_request import PublishedPackageVisibilityRequest
from scheduler_api.service.package_index import (
    PACKAGE_ARCHIVE_NAME,
    PACKAGE_STATUS_VALUES,
    PublishedPackageAlreadyExistsError,
    PublishedPackageOwnershipError,
    PublishedPackageNotFoundError,
    PublishedPackageQuotaError,
    PublishedPackageStatusError,
    PublishedPackageTagNotFoundError,
    PublishedPackageVersionNotFoundError,
    package_index_service,
)
from scheduler_api.service.package_registry import (
    PACKAGE_STATE_ACTIVE,
    PACKAGE_VISIBILITY_INTERNAL,
    PackageRegistryConflictError,
    PackageRegistryNotFoundError,
    PackageRegistryOwnershipError,
    PackageRegistryVisibilityError,
    package_registry_service,
)
from shared.models.manifest import PackageManifest


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
                raise bad_request("Archive contains invalid paths.")
        if "manifest.json" not in names:
            raise bad_request("manifest.json must exist at the archive root.")
        with zip_file.open("manifest.json") as handle:
            return json.load(handle)


class PublishedPackagesApiImpl(BasePublishedPackagesApi):
    async def list_published_packages(self) -> PackageList:
        token = require_roles(*WORKFLOW_VIEW_ROLES)
        owner_id = token.sub if token else None
        is_admin = "admin" in (token.roles if token else [])
        summaries = package_index_service.list_packages()
        registry_by_name = {
            entry.name: entry
            for entry in package_registry_service.list_by_names(
                [summary["name"] for summary in summaries]
            )
        }
        items = [
            PackageSummary(
                name=summary["name"],
                description=summary.get("description"),
                latestVersion=summary.get("latestVersion"),
                defaultVersion=summary.get("defaultVersion"),
                versions=summary.get("versions", []),
                distTags=summary.get("distTags"),
                ownerId=_resolve_owner_id(summary["name"], registry_by_name),
                visibility=_resolve_visibility(summary["name"], registry_by_name),
                state=_resolve_state(summary["name"], registry_by_name),
            )
            for summary in summaries
            if _can_read_package(summary["name"], registry_by_name, owner_id, is_admin)
        ]
        return PackageList(items=items)

    async def upload_published_package(self, file: UploadFile) -> PackageDetail:
        token = require_roles(*WORKFLOW_EDIT_ROLES)
        owner_id = token.sub if token else None
        if not owner_id:
            raise forbidden("Authentication required.")
        if not file or not file.filename:
            raise bad_request("Package archive is required.")

        settings = get_api_settings()
        published_root = settings.published_packages_root
        tmp_dir = Path(tempfile.mkdtemp(prefix="pkg-upload-"))
        tmp_path = tmp_dir / "package.zip"
        try:
            with tmp_path.open("wb") as handle:
                while True:
                    chunk = await file.read(1024 * 1024)
                    if not chunk:
                        break
                    handle.write(chunk)

            try:
                manifest_payload = _read_manifest_from_zip(tmp_path)
                manifest_model = PackageManifest.model_validate(manifest_payload)
            except HTTPException:
                raise
            except Exception as exc:
                raise bad_request("Invalid package manifest.") from exc

            package_name = manifest_model.name
            package_version = manifest_model.version
            archive_size_bytes = tmp_path.stat().st_size
            try:
                package_index_service.ensure_storage_quota(
                    owner_id=owner_id,
                    name=package_name,
                    incoming_bytes=archive_size_bytes,
                )
            except PublishedPackageQuotaError as exc:
                raise bad_request(str(exc)) from exc
            try:
                registry = package_registry_service.ensure_publish_access(
                    package_name,
                    actor_id=owner_id,
                    require_existing=False,
                )
            except PackageRegistryOwnershipError as exc:
                raise forbidden(str(exc)) from exc
            except PackageRegistryConflictError as exc:
                raise conflict(str(exc)) from exc
            except PackageRegistryVisibilityError as exc:
                raise bad_request(str(exc)) from exc
            target_dir = published_root / package_name / package_version
            if target_dir.exists():
                raise conflict(f"Package '{package_name}' version '{package_version}' already exists.")

            target_dir.mkdir(parents=True, exist_ok=False)
            try:
                archive_path = target_dir / PACKAGE_ARCHIVE_NAME
                shutil.copyfile(tmp_path, archive_path)
                try:
                    detail = package_index_service.register_package(
                        manifest_model,
                        archive_path,
                        owner_id=owner_id,
                    )
                except PublishedPackageAlreadyExistsError as exc:
                    raise conflict(str(exc)) from exc
                except PublishedPackageOwnershipError as exc:
                    raise forbidden(str(exc)) from exc
            except Exception:
                shutil.rmtree(target_dir, ignore_errors=True)
                raise
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

        manifest_api_model = ApiPackageManifest.from_dict(detail["manifest"])
        payload = PackageDetail(
            name=detail["name"],
            version=detail["version"],
            availableVersions=detail.get("availableVersions"),
            manifest=manifest_api_model,
            status=detail.get("status"),
            distTags=detail.get("distTags"),
            archiveSha256=detail.get("archiveSha256"),
            archiveSizeBytes=detail.get("archiveSizeBytes"),
            ownerId=registry.owner_id if registry else None,
            visibility=registry.visibility if registry else PACKAGE_VISIBILITY_INTERNAL,
            state=registry.state if registry else PACKAGE_STATE_ACTIVE,
        )
        record_audit_event(
            actor_id=owner_id,
            action="package.publish",
            target_type="package",
            target_id=detail["name"],
            metadata={
                "version": detail.get("version"),
            },
        )
        archive_sha = detail.get("archiveSha256")
        if archive_sha:
            return JSONResponse(
                content=payload.model_dump(by_alias=True, exclude_none=True),
                headers={"X-Package-Archive-Sha256": str(archive_sha)},
            )
        return payload

    async def gc_published_packages(
        self,
        published_package_gc_request: PublishedPackageGcRequest,
    ) -> PublishedPackageGcResult:
        token = require_roles("admin")
        if published_package_gc_request is None:
            raise bad_request("GC payload is required.")
        items, total_bytes = package_index_service.gc_packages(
            package_name=published_package_gc_request.package_name,
            max_versions=published_package_gc_request.max_versions,
            dry_run=bool(published_package_gc_request.dry_run),
        )
        record_audit_event(
            actor_id=token.sub,
            action="package.gc",
            target_type="package",
            target_id=published_package_gc_request.package_name or "*",
            metadata={
                "maxVersions": published_package_gc_request.max_versions,
                "dryRun": bool(published_package_gc_request.dry_run),
                "removedCount": len(items),
                "totalBytes": total_bytes,
            },
        )
        return PublishedPackageGcResult(
            items=[
                PublishedPackageGcItem(
                    name=item.name,
                    version=item.version,
                    sizeBytes=item.size_bytes,
                    archivePath=item.archive_path,
                )
                for item in items
            ],
            totalBytes=total_bytes,
        )

    async def get_published_package(self, packageName: str, version: str | None) -> PackageDetail:
        token = require_roles(*WORKFLOW_VIEW_ROLES)
        owner_id = token.sub if token else None
        is_admin = "admin" in (token.roles if token else [])
        registry = package_registry_service.get(packageName)
        if registry and not package_registry_service.can_read(
            registry,
            actor_id=owner_id,
            is_admin=is_admin,
        ):
            raise forbidden("Package is private.")
        try:
            detail = package_index_service.get_package_detail(packageName, version)
        except PublishedPackageNotFoundError as exc:
            raise not_found(str(exc), error="package_not_found") from exc
        except PublishedPackageVersionNotFoundError as exc:
            raise not_found(str(exc), error="package_version_not_found") from exc

        manifest_api_model = ApiPackageManifest.from_dict(detail["manifest"])
        payload = PackageDetail(
            name=detail["name"],
            version=detail["version"],
            availableVersions=detail.get("availableVersions"),
            manifest=manifest_api_model,
            status=detail.get("status"),
            distTags=detail.get("distTags"),
            archiveSha256=detail.get("archiveSha256"),
            archiveSizeBytes=detail.get("archiveSizeBytes"),
            ownerId=registry.owner_id if registry else None,
            visibility=registry.visibility if registry else PACKAGE_VISIBILITY_INTERNAL,
            state=registry.state if registry else PACKAGE_STATE_ACTIVE,
        )
        archive_sha = detail.get("archiveSha256")
        if archive_sha:
            return JSONResponse(
                content=payload.model_dump(by_alias=True, exclude_none=True),
                headers={"X-Package-Archive-Sha256": str(archive_sha)},
            )
        return payload

    async def get_published_package_registry(self, packageName: str) -> PublishedPackageRegistry:
        token = require_roles(*WORKFLOW_VIEW_ROLES)
        owner_id = token.sub if token else None
        is_admin = "admin" in (token.roles if token else [])
        registry = package_registry_service.get(packageName)
        if registry is None:
            raise not_found(f"Package '{packageName}' not found.", error="package_not_found")
        if not package_registry_service.can_read(
            registry,
            actor_id=owner_id,
            is_admin=is_admin,
        ):
            raise forbidden("Package is private.")
        return _to_registry_model(registry)

    async def download_published_package(self, packageName: str, version: str | None) -> FileResponse:
        token = require_roles(*WORKFLOW_VIEW_ROLES)
        owner_id = token.sub if token else None
        is_admin = "admin" in (token.roles if token else [])
        registry = package_registry_service.get(packageName)
        if registry and not package_registry_service.can_read(
            registry,
            actor_id=owner_id,
            is_admin=is_admin,
        ):
            raise forbidden("Package is private.")
        try:
            archive_path, archive_sha256, resolved_version = package_index_service.get_archive_path(
                packageName,
                version,
            )
        except PublishedPackageNotFoundError as exc:
            raise not_found(str(exc), error="package_not_found") from exc
        except PublishedPackageVersionNotFoundError as exc:
            raise not_found(str(exc), error="package_version_not_found") from exc

        if not archive_path.is_file():
            raise not_found(
                f"Archive missing for '{packageName}' version '{resolved_version}'.",
                error="package_archive_missing",
            )

        headers = {}
        if archive_sha256:
            headers["X-Package-Archive-Sha256"] = archive_sha256
        filename = f"{packageName}-{resolved_version}.zip"
        return FileResponse(archive_path, media_type="application/zip", filename=filename, headers=headers)

    async def reserve_published_package(
        self,
        packageName: str,
        published_package_reserve_request: PublishedPackageReserveRequest | None,
    ) -> PublishedPackageRegistry:
        token = require_roles(*WORKFLOW_EDIT_ROLES)
        owner_id = token.sub if token else None
        if not owner_id:
            raise forbidden("Authentication required.")
        visibility = PACKAGE_VISIBILITY_INTERNAL
        if published_package_reserve_request is not None:
            visibility = published_package_reserve_request.visibility or visibility
        try:
            registry = package_registry_service.reserve(
                packageName,
                owner_id=owner_id,
                visibility=visibility,
                actor_id=owner_id,
            )
        except PackageRegistryConflictError as exc:
            raise conflict(str(exc)) from exc
        except PackageRegistryVisibilityError as exc:
            raise bad_request(str(exc)) from exc
        record_audit_event(
            actor_id=owner_id,
            action="package.reserve",
            target_type="package",
            target_id=packageName,
            metadata={"visibility": visibility},
        )
        return _to_registry_model(registry)

    async def set_published_package_version_status(
        self,
        packageName: str,
        version: str,
        published_package_status_request: PublishedPackageStatusRequest,
    ) -> PackageDetail:
        token = require_roles(*WORKFLOW_EDIT_ROLES)
        owner_id = token.sub if token else None
        if not owner_id:
            raise forbidden("Authentication required.")
        if published_package_status_request is None:
            raise bad_request("Package status payload is required.")
        try:
            registry = package_registry_service.ensure_publish_access(
                packageName,
                actor_id=owner_id,
                require_existing=True,
            )
        except PackageRegistryNotFoundError as exc:
            raise not_found(str(exc), error="package_not_found") from exc
        except PackageRegistryOwnershipError as exc:
            raise forbidden(str(exc)) from exc
        except PackageRegistryVisibilityError as exc:
            raise bad_request(str(exc)) from exc
        status = published_package_status_request.status
        if status not in PACKAGE_STATUS_VALUES:
            raise bad_request("Invalid package status.")
        try:
            detail = package_index_service.set_package_status(
                packageName,
                version,
                status,
                owner_id=owner_id,
            )
        except PublishedPackageNotFoundError as exc:
            raise not_found(str(exc), error="package_not_found") from exc
        except PublishedPackageVersionNotFoundError as exc:
            raise not_found(str(exc), error="package_version_not_found") from exc
        except PublishedPackageOwnershipError as exc:
            raise forbidden(str(exc)) from exc
        except PublishedPackageStatusError as exc:
            raise bad_request(str(exc)) from exc

        manifest_api_model = ApiPackageManifest.from_dict(detail["manifest"])
        payload = PackageDetail(
            name=detail["name"],
            version=detail["version"],
            availableVersions=detail.get("availableVersions"),
            manifest=manifest_api_model,
            status=detail.get("status"),
            distTags=detail.get("distTags"),
            archiveSha256=detail.get("archiveSha256"),
            archiveSizeBytes=detail.get("archiveSizeBytes"),
            ownerId=registry.owner_id if registry else None,
            visibility=registry.visibility if registry else PACKAGE_VISIBILITY_INTERNAL,
            state=registry.state if registry else PACKAGE_STATE_ACTIVE,
        )
        record_audit_event(
            actor_id=owner_id,
            action="package.status.update",
            target_type="package",
            target_id=detail["name"],
            metadata={"version": detail.get("version"), "status": status},
        )
        return payload

    async def set_published_package_tag(
        self,
        packageName: str,
        tag: str,
        published_package_tag_request: PublishedPackageTagRequest,
    ) -> None:
        token = require_roles(*WORKFLOW_EDIT_ROLES)
        owner_id = token.sub if token else None
        if not owner_id:
            raise forbidden("Authentication required.")
        if published_package_tag_request is None:
            raise bad_request("Package tag payload is required.")
        try:
            package_registry_service.ensure_publish_access(
                packageName,
                actor_id=owner_id,
                require_existing=True,
            )
        except PackageRegistryNotFoundError as exc:
            raise not_found(str(exc), error="package_not_found") from exc
        except PackageRegistryOwnershipError as exc:
            raise forbidden(str(exc)) from exc
        except PackageRegistryVisibilityError as exc:
            raise bad_request(str(exc)) from exc
        try:
            package_index_service.set_dist_tag(
                packageName,
                tag,
                published_package_tag_request.version,
                owner_id=owner_id,
            )
        except PublishedPackageNotFoundError as exc:
            raise not_found(str(exc), error="package_not_found") from exc
        except PublishedPackageVersionNotFoundError as exc:
            raise not_found(str(exc), error="package_version_not_found") from exc
        except PublishedPackageOwnershipError as exc:
            raise forbidden(str(exc)) from exc
        record_audit_event(
            actor_id=owner_id,
            action="package.tag.set",
            target_type="package",
            target_id=packageName,
            metadata={"tag": tag, "version": published_package_tag_request.version},
        )

    async def delete_published_package_tag(
        self,
        packageName: str,
        tag: str,
    ) -> None:
        token = require_roles(*WORKFLOW_EDIT_ROLES)
        owner_id = token.sub if token else None
        if not owner_id:
            raise forbidden("Authentication required.")
        try:
            package_registry_service.ensure_publish_access(
                packageName,
                actor_id=owner_id,
                require_existing=True,
            )
        except PackageRegistryNotFoundError as exc:
            raise not_found(str(exc), error="package_not_found") from exc
        except PackageRegistryOwnershipError as exc:
            raise forbidden(str(exc)) from exc
        except PackageRegistryVisibilityError as exc:
            raise bad_request(str(exc)) from exc
        try:
            package_index_service.delete_dist_tag(
                packageName,
                tag,
                owner_id=owner_id,
            )
        except PublishedPackageNotFoundError as exc:
            raise not_found(str(exc), error="package_not_found") from exc
        except PublishedPackageTagNotFoundError as exc:
            raise not_found(str(exc), error="package_tag_not_found") from exc
        except PublishedPackageOwnershipError as exc:
            raise forbidden(str(exc)) from exc
        record_audit_event(
            actor_id=owner_id,
            action="package.tag.delete",
            target_type="package",
            target_id=packageName,
            metadata={"tag": tag},
        )

    async def update_published_package_visibility(
        self,
        packageName: str,
        published_package_visibility_request: PublishedPackageVisibilityRequest,
    ) -> PublishedPackageRegistry:
        token = require_roles(*WORKFLOW_EDIT_ROLES)
        owner_id = token.sub if token else None
        if not owner_id:
            raise forbidden("Authentication required.")
        if published_package_visibility_request is None:
            raise bad_request("Package visibility payload is required.")
        is_admin = "admin" in (token.roles if token else [])
        try:
            registry = package_registry_service.update_visibility(
                packageName,
                visibility=published_package_visibility_request.visibility,
                actor_id=owner_id,
                is_admin=is_admin,
            )
        except PackageRegistryNotFoundError as exc:
            raise not_found(str(exc), error="package_not_found") from exc
        except PackageRegistryOwnershipError as exc:
            raise forbidden(str(exc)) from exc
        except PackageRegistryVisibilityError as exc:
            raise bad_request(str(exc)) from exc
        record_audit_event(
            actor_id=owner_id,
            action="package.visibility.update",
            target_type="package",
            target_id=packageName,
            metadata={"visibility": published_package_visibility_request.visibility},
        )
        return _to_registry_model(registry)

    async def transfer_published_package(
        self,
        packageName: str,
        published_package_transfer_request: PublishedPackageTransferRequest,
    ) -> PublishedPackageRegistry:
        token = require_roles(*WORKFLOW_EDIT_ROLES)
        owner_id = token.sub if token else None
        if not owner_id:
            raise forbidden("Authentication required.")
        if published_package_transfer_request is None:
            raise bad_request("Package transfer payload is required.")
        new_owner_id = published_package_transfer_request.new_owner_id
        if not new_owner_id:
            raise bad_request("newOwnerId is required.")
        is_admin = "admin" in (token.roles if token else [])
        existing = package_registry_service.get(packageName)
        if existing is None:
            raise not_found(f"Package '{packageName}' not found.", error="package_not_found")
        try:
            registry = package_registry_service.transfer_owner(
                packageName,
                new_owner_id=new_owner_id,
                actor_id=owner_id,
                is_admin=is_admin,
            )
        except PackageRegistryNotFoundError as exc:
            raise not_found(str(exc), error="package_not_found") from exc
        except PackageRegistryOwnershipError as exc:
            raise forbidden(str(exc)) from exc
        record_audit_event(
            actor_id=owner_id,
            action="package.transfer",
            target_type="package",
            target_id=packageName,
            metadata={"from": existing.owner_id, "to": new_owner_id},
        )
        return _to_registry_model(registry)


def _resolve_owner_id(package_name: str, registry_by_name) -> str | None:
    entry = registry_by_name.get(package_name)
    return entry.owner_id if entry else None


def _resolve_visibility(package_name: str, registry_by_name) -> str:
    entry = registry_by_name.get(package_name)
    return entry.visibility if entry else PACKAGE_VISIBILITY_INTERNAL


def _resolve_state(package_name: str, registry_by_name) -> str:
    entry = registry_by_name.get(package_name)
    return entry.state if entry else PACKAGE_STATE_ACTIVE


def _can_read_package(
    package_name: str,
    registry_by_name,
    owner_id: str | None,
    is_admin: bool,
) -> bool:
    entry = registry_by_name.get(package_name)
    if entry is None:
        return True
    if not owner_id:
        return False
    return package_registry_service.can_read(
        entry,
        actor_id=owner_id,
        is_admin=is_admin,
    )


def _to_registry_model(registry) -> PublishedPackageRegistry:
    return PublishedPackageRegistry(
        name=registry.name,
        ownerId=registry.owner_id,
        visibility=registry.visibility,
        state=registry.state,
        createdAt=registry.created_at,
        updatedAt=registry.updated_at,
        createdBy=registry.created_by,
        updatedBy=registry.updated_by,
    )
