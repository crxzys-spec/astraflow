from __future__ import annotations

from fastapi import UploadFile
from fastapi.responses import Response
import io
import json
import zipfile
from pathlib import Path

from scheduler_api.apis.hub_packages_api_base import BaseHubPackagesApi
from scheduler_api.auth.roles import WORKFLOW_EDIT_ROLES, WORKFLOW_VIEW_ROLES, require_roles
from scheduler_api.http.errors import bad_request, conflict, forbidden, not_found
from scheduler_api.infra.catalog import (
    PackageCatalogError,
    PackageNotFoundError,
    PackageVersionNotFoundError,
    LOCAL_OWNER,
    catalog,
)
from scheduler_api.infra.catalog.hub_link import HUB_LINK_FILENAME, write_hub_link
from scheduler_api.infra.catalog.package_catalog import _version_key
from scheduler_api.models.hub_local_package_publish_request import HubLocalPackagePublishRequest
from scheduler_api.models.hub_package_detail import HubPackageDetail
from scheduler_api.models.hub_package_install_request import HubPackageInstallRequest
from scheduler_api.models.hub_package_install_response import HubPackageInstallResponse
from scheduler_api.models.hub_package_list_response import HubPackageListResponse
from scheduler_api.models.hub_package_version_detail import HubPackageVersionDetail
from scheduler_api.models.hub_visibility import HubVisibility
from scheduler_api.service.hub_client import (
    HubClient,
    HubClientError,
    HubConflictError,
    HubDownloadResult,
    HubNotConfiguredError,
    HubNotFoundError,
    HubUnauthorizedError,
)
from scheduler_api.service.hub_mirror import HubMirrorError, hub_mirror_service


def _visibility_value(value: HubVisibility | str | None) -> str | None:
    if value is None:
        return None
    return value.value if hasattr(value, "value") else str(value)


def _is_unsafe_entry(entry_name: str) -> bool:
    entry_path = Path(entry_name)
    if entry_path.is_absolute():
        return True
    return ".." in entry_path.parts


def _read_manifest_from_archive(archive_bytes: bytes) -> dict:
    try:
        with zipfile.ZipFile(io.BytesIO(archive_bytes)) as zip_file:
            names = {info.filename for info in zip_file.infolist() if not info.is_dir()}
            for name in names:
                if _is_unsafe_entry(name):
                    raise bad_request("Archive contains invalid paths.")
            if "manifest.json" not in names:
                raise bad_request("manifest.json must exist at the archive root.")
            with zip_file.open("manifest.json") as handle:
                payload = json.load(handle)
    except zipfile.BadZipFile as exc:
        raise bad_request("Invalid package archive.") from exc
    except json.JSONDecodeError as exc:
        raise bad_request("Invalid manifest.json content.") from exc
    if not isinstance(payload, dict):
        raise bad_request("Invalid manifest.json content.")
    return payload


def _build_archive_from_dir(package_dir: Path) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as zip_file:
        for path in package_dir.rglob("*"):
            if not path.is_file():
                continue
            if path.name == HUB_LINK_FILENAME:
                continue
            if "__pycache__" in path.parts:
                continue
            rel_path = path.relative_to(package_dir)
            zip_file.write(path, rel_path.as_posix())
    return buffer.getvalue()


def _resolve_local_package(
    name: str,
    version: str | None,
) -> tuple[str, Path, dict]:
    versions = catalog.list_versions(name, owner=LOCAL_OWNER)
    if not versions:
        raise PackageNotFoundError(f"Package '{name}' not found.")
    target_version = version or versions[0]
    if target_version not in versions:
        raise PackageVersionNotFoundError(
            f"Package '{name}' has no version '{target_version}'."
        )
    package_dir = catalog.packages_root / LOCAL_OWNER / name / target_version
    if not package_dir.exists():
        legacy_dir = catalog.packages_root / name / target_version
        if legacy_dir.exists():
            package_dir = legacy_dir
    manifest_path = package_dir / "manifest.json"
    if not manifest_path.is_file():
        raise PackageCatalogError(f"manifest.json missing for {name}@{target_version}.")
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise PackageCatalogError("manifest.json is invalid.")
    if payload.get("name") != name or payload.get("version") != target_version:
        raise PackageCatalogError("manifest.json does not match requested package.")
    return target_version, package_dir, payload


class HubPackagesApiImpl(BaseHubPackagesApi):
    async def list_hub_packages(
        self,
        q: str | None,
        tag: str | None,
        owner: str | None,
        page: int | None,
        page_size: int | None,
    ) -> HubPackageListResponse:
        require_roles(*WORKFLOW_VIEW_ROLES)
        try:
            payload = HubClient.from_settings().list_packages(
                query=q,
                tag=tag,
                owner=owner,
                page=page,
                page_size=page_size,
            )
        except HubNotConfiguredError as exc:
            raise bad_request(str(exc), error="hub_not_configured") from exc
        except HubUnauthorizedError as exc:
            raise forbidden(str(exc), error="hub_unauthorized") from exc
        except HubClientError as exc:
            raise bad_request(str(exc), error="hub_request_failed") from exc
        return HubPackageListResponse.from_dict(payload)

    async def publish_hub_package(
        self,
        file: UploadFile,
        visibility: HubVisibility | None,
        summary: str | None,
        readme: str | None,
        tags: list[str] | None,
    ) -> HubPackageVersionDetail:
        require_roles(*WORKFLOW_EDIT_ROLES)
        if file is None or not file.filename:
            raise bad_request("Package archive is required.")
        archive_bytes = await file.read()
        if not archive_bytes:
            raise bad_request("Package archive is required.")
        manifest_payload = _read_manifest_from_archive(archive_bytes)
        package_name = manifest_payload.get("name")
        package_version = manifest_payload.get("version")
        if not isinstance(package_name, str) or not isinstance(package_version, str):
            raise bad_request("Manifest must include name and version.")
        try:
            payload = HubClient.from_settings().publish_package(
                file_obj=io.BytesIO(archive_bytes),
                filename=file.filename,
                visibility=_visibility_value(visibility),
                summary=summary,
                readme=readme,
                tags=tags,
            )
        except HubNotConfiguredError as exc:
            raise bad_request(str(exc), error="hub_not_configured") from exc
        except HubUnauthorizedError as exc:
            raise forbidden(str(exc), error="hub_unauthorized") from exc
        except HubConflictError as exc:
            raise conflict(str(exc), error="hub_conflict") from exc
        except HubClientError as exc:
            raise bad_request(str(exc), error="hub_request_failed") from exc
        owner_id = payload.get("ownerId")
        hub_name = f"{owner_id}/{package_name}" if owner_id else package_name
        hub_meta = {
            "hubName": hub_name,
            "hubVersion": package_version,
            "ownerId": owner_id,
            "ownerName": payload.get("ownerName"),
            "visibility": payload.get("visibility"),
            "publishedAt": payload.get("publishedAt") or payload.get("updatedAt"),
            "archiveSha256": payload.get("archiveSha256"),
        }
        target_dir = catalog.packages_root / LOCAL_OWNER / package_name / package_version
        if not target_dir.exists():
            legacy_dir = catalog.packages_root / package_name / package_version
            if legacy_dir.exists():
                target_dir = legacy_dir
        if target_dir.exists():
            write_hub_link(target_dir, hub_meta)
        return HubPackageVersionDetail.from_dict(payload)

    async def publish_hub_package_local(
        self,
        hub_local_package_publish_request: HubLocalPackagePublishRequest,
    ) -> HubPackageVersionDetail:
        require_roles(*WORKFLOW_EDIT_ROLES)
        if hub_local_package_publish_request is None:
            raise bad_request("Publish payload is required.")
        package_name = hub_local_package_publish_request.name
        version = hub_local_package_publish_request.version
        try:
            package_version, package_dir, _ = _resolve_local_package(package_name, version)
        except PackageNotFoundError as exc:
            raise not_found(str(exc), error="package_not_found") from exc
        except PackageVersionNotFoundError as exc:
            raise not_found(str(exc), error="package_version_not_found") from exc
        except PackageCatalogError as exc:
            raise bad_request(str(exc), error="package_catalog_error") from exc
        archive_bytes = _build_archive_from_dir(package_dir)
        if not archive_bytes:
            raise bad_request("Package archive is empty.")
        filename = f"{package_name}-{package_version}.zip"
        try:
            payload = HubClient.from_settings().publish_package(
                file_obj=io.BytesIO(archive_bytes),
                filename=filename,
                visibility=_visibility_value(hub_local_package_publish_request.visibility),
                summary=hub_local_package_publish_request.summary,
                readme=hub_local_package_publish_request.readme,
                tags=hub_local_package_publish_request.tags,
            )
        except HubNotConfiguredError as exc:
            raise bad_request(str(exc), error="hub_not_configured") from exc
        except HubUnauthorizedError as exc:
            raise forbidden(str(exc), error="hub_unauthorized") from exc
        except HubConflictError as exc:
            raise conflict(str(exc), error="hub_conflict") from exc
        except HubClientError as exc:
            raise bad_request(str(exc), error="hub_request_failed") from exc
        owner_id = payload.get("ownerId")
        hub_name = f"{owner_id}/{package_name}" if owner_id else package_name
        hub_meta = {
            "hubName": hub_name,
            "hubVersion": package_version,
            "ownerId": owner_id,
            "ownerName": payload.get("ownerName"),
            "visibility": payload.get("visibility"),
            "publishedAt": payload.get("publishedAt") or payload.get("updatedAt"),
            "archiveSha256": payload.get("archiveSha256"),
        }
        target_dir = catalog.packages_root / LOCAL_OWNER / package_name / package_version
        if not target_dir.exists():
            legacy_dir = catalog.packages_root / package_name / package_version
            if legacy_dir.exists():
                target_dir = legacy_dir
        if target_dir.exists():
            write_hub_link(target_dir, hub_meta)
        return HubPackageVersionDetail.from_dict(payload)

    async def get_hub_package(self, owner: str, name: str) -> HubPackageDetail:
        require_roles(*WORKFLOW_VIEW_ROLES)
        package_ref = f"{owner}/{name}"
        try:
            payload = HubClient.from_settings().get_package(package_ref)
        except HubNotConfiguredError as exc:
            raise bad_request(str(exc), error="hub_not_configured") from exc
        except HubNotFoundError as exc:
            raise not_found(str(exc), error="hub_not_found") from exc
        except HubUnauthorizedError as exc:
            raise forbidden(str(exc), error="hub_unauthorized") from exc
        except HubClientError as exc:
            raise bad_request(str(exc), error="hub_request_failed") from exc
        return HubPackageDetail.from_dict(payload)

    async def get_hub_package_version(
        self,
        owner: str,
        name: str,
        version: str,
    ) -> HubPackageVersionDetail:
        require_roles(*WORKFLOW_VIEW_ROLES)
        package_ref = f"{owner}/{name}"
        try:
            payload = HubClient.from_settings().get_package_version(package_ref, version)
        except HubNotConfiguredError as exc:
            raise bad_request(str(exc), error="hub_not_configured") from exc
        except HubNotFoundError as exc:
            raise not_found(str(exc), error="hub_not_found") from exc
        except HubUnauthorizedError as exc:
            raise forbidden(str(exc), error="hub_unauthorized") from exc
        except HubClientError as exc:
            raise bad_request(str(exc), error="hub_request_failed") from exc
        return HubPackageVersionDetail.from_dict(payload)

    async def download_hub_package_archive(
        self,
        owner: str,
        name: str,
        version: str | None,
    ) -> Response:
        require_roles(*WORKFLOW_VIEW_ROLES)
        package_ref = f"{owner}/{name}"
        try:
            content = HubClient.from_settings().download_package_archive(
                package_ref,
                version=version,
            )
        except HubNotConfiguredError as exc:
            raise bad_request(str(exc), error="hub_not_configured") from exc
        except HubNotFoundError as exc:
            raise not_found(str(exc), error="hub_not_found") from exc
        except HubUnauthorizedError as exc:
            raise forbidden(str(exc), error="hub_unauthorized") from exc
        except HubClientError as exc:
            raise bad_request(str(exc), error="hub_request_failed") from exc
        if isinstance(content, HubDownloadResult):
            data = content.path.read_bytes()
        else:
            data = content
        return Response(content=data, media_type="application/zip")

    async def install_hub_package(
        self,
        owner: str,
        name: str,
        hub_package_install_request: HubPackageInstallRequest | None,
    ) -> HubPackageInstallResponse:
        require_roles(*WORKFLOW_EDIT_ROLES)
        package_ref = f"{owner}/{name}"
        version_value = None
        if hub_package_install_request and hub_package_install_request.version:
            version_value = hub_package_install_request.version
        if not version_value:
            try:
                detail = HubClient.from_settings().get_package(package_ref)
            except HubNotConfiguredError as exc:
                raise bad_request(str(exc), error="hub_not_configured") from exc
            except HubNotFoundError as exc:
                raise not_found(str(exc), error="hub_not_found") from exc
            except HubUnauthorizedError as exc:
                raise forbidden(str(exc), error="hub_unauthorized") from exc
            except HubClientError as exc:
                raise bad_request(str(exc), error="hub_request_failed") from exc
            versions = detail.get("versions")
            if not isinstance(versions, list) or not versions:
                raise not_found("Hub package has no versions.", error="hub_not_found")
            version_value = max((str(item) for item in versions), key=_version_key)

        try:
            hub_mirror_service.ensure_package(
                name=name,
                version=version_value,
                owner=owner,
            )
            hub_mirror_service.install_to_catalog(
                name=name,
                version=version_value,
                owner=owner,
            )
        except HubMirrorError as exc:
            raise bad_request(str(exc), error="hub_install_failed") from exc

        return HubPackageInstallResponse(
            name=package_ref,
            version=version_value,
            installed=True,
        )

    async def uninstall_hub_package(
        self,
        owner: str,
        name: str,
        hub_package_install_request: HubPackageInstallRequest | None,
    ) -> HubPackageInstallResponse:
        require_roles(*WORKFLOW_EDIT_ROLES)
        version_value = None
        if hub_package_install_request and hub_package_install_request.version:
            version_value = hub_package_install_request.version
        try:
            removed_versions = hub_mirror_service.uninstall_from_catalog(
                name=name,
                version=version_value,
                owner=owner,
            )
        except HubMirrorError as exc:
            raise bad_request(str(exc), error="hub_uninstall_failed") from exc
        resolved_version = version_value or (removed_versions[0] if removed_versions else "all")
        package_ref = f"{owner}/{name}"
        return HubPackageInstallResponse(
            name=package_ref,
            version=resolved_version,
            installed=False,
        )
