from __future__ import annotations

from datetime import datetime, timezone
from math import ceil
import hashlib
import io
import json
import zipfile

from fastapi import HTTPException, UploadFile, status
from fastapi.responses import Response

from hub_api.repo.audit import record_audit_event
from hub_api.repo.packages import (
    DEFAULT_VISIBILITY,
    add_package_permission,
    delete_package_permission,
    delete_package_tag_record,
    get_package_record,
    get_package_version_record,
    list_package_permissions,
    list_packages,
    publish_package_version,
    reserve_package_record,
    set_package_tag_record,
    transfer_package_record,
    update_package_permission,
    update_package_visibility_record,
)
from hub_api.repo.accounts import get_account
from hub_api.repo.tokens import get_token_record
from hub_api.models.hub_package_detail import HubPackageDetail
from hub_api.models.hub_package_summary import HubPackageSummary
from hub_api.models.package_list_response import PackageListResponse
from hub_api.models.package_permission import PackagePermission
from hub_api.models.package_permission_create_request import PackagePermissionCreateRequest
from hub_api.models.package_permission_list import PackagePermissionList
from hub_api.models.package_permission_update_request import PackagePermissionUpdateRequest
from hub_api.models.package_registry import PackageRegistry
from hub_api.models.package_reserve_request import PackageReserveRequest
from hub_api.models.package_tag_request import PackageTagRequest
from hub_api.models.package_transfer_request import PackageTransferRequest
from hub_api.models.package_version_detail import PackageVersionDetail
from hub_api.models.package_visibility_request import PackageVisibilityRequest
from hub_api.models.page_meta import PageMeta
from hub_api.models.visibility import Visibility
from hub_api.security_api import (
    get_current_actor,
    get_current_token_value,
    is_admin,
    require_actor,
)
from hub_api.services.permissions import get_package_role_for_user
from hub_api.storage import resolve_storage_path


_ROLE_RANK = {"reader": 1, "maintainer": 2, "owner": 3}


def _normalize(value: str | None) -> str:
    return value.lower().strip() if value else ""


def _enum_value(value) -> str:
    return value.value if hasattr(value, "value") else str(value)


def _match_query(record: dict, query: str) -> bool:
    if not query:
        return True
    candidates = [
        record.get("name"),
        record.get("description"),
        record.get("ownerName"),
    ]
    query_lower = query.lower()
    return any(isinstance(item, str) and query_lower in item.lower() for item in candidates)


def _match_tag(record: dict, tag: str) -> bool:
    if not tag:
        return True
    tags = record.get("tags")
    if not isinstance(tags, list):
        return False
    tag_lower = tag.lower()
    return any(isinstance(item, str) and item.lower() == tag_lower for item in tags)


def _match_owner(record: dict, owner: str) -> bool:
    if not owner:
        return True
    owner_lower = owner.lower()
    owner_id = record.get("ownerId")
    owner_name = record.get("ownerName")
    if isinstance(owner_id, str) and owner_id.lower() == owner_lower:
        return True
    if isinstance(owner_name, str) and owner_name.lower() == owner_lower:
        return True
    return False


def _paginate(items: list[dict], page: int, page_size: int) -> tuple[list[dict], PageMeta]:
    total = len(items)
    total_pages = ceil(total / page_size) if total else 0
    start = (page - 1) * page_size
    end = start + page_size
    slice_items = items[start:end] if start < total else []
    meta = PageMeta(
        page=page,
        pageSize=page_size,
        total=total,
        totalPages=total_pages,
    )
    return slice_items, meta


def _summary_from_record(record: dict) -> HubPackageSummary:
    payload = {
        "name": record.get("name"),
        "latestVersion": record.get("latestVersion"),
        "description": record.get("description"),
        "tags": record.get("tags"),
        "ownerId": record.get("ownerId"),
        "ownerName": record.get("ownerName"),
        "updatedAt": record.get("updatedAt"),
        "visibility": record.get("visibility"),
    }
    return HubPackageSummary.from_dict(payload)


def _detail_from_record(record: dict) -> HubPackageDetail:
    payload = {
        "name": record.get("name"),
        "description": record.get("description"),
        "readme": record.get("readme"),
        "versions": list(record.get("versions", {}).keys()),
        "distTags": record.get("distTags"),
        "tags": record.get("tags"),
        "ownerId": record.get("ownerId"),
        "ownerName": record.get("ownerName"),
        "updatedAt": record.get("updatedAt"),
        "visibility": record.get("visibility"),
    }
    return HubPackageDetail.from_dict(payload)


def _registry_from_record(record: dict) -> PackageRegistry:
    payload = {
        "name": record.get("name"),
        "ownerId": record.get("ownerId"),
        "visibility": record.get("visibility"),
        "createdAt": record.get("createdAt"),
        "updatedAt": record.get("updatedAt"),
    }
    return PackageRegistry.from_dict(payload)


def _version_detail_from_record(record: dict) -> PackageVersionDetail:
    payload = {
        key: value
        for key, value in record.items()
        if key not in {"archive", "archivePath"}
    }
    return PackageVersionDetail.from_dict(payload)


def _visibility_value(value: Visibility | str | None) -> str:
    if value is None:
        return DEFAULT_VISIBILITY
    return value.value if hasattr(value, "value") else str(value)


def _normalize_tags(value: list[str] | str | None) -> list[str] | None:
    if value is None:
        return None
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str) and item.strip()]
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return None


def _ensure_valid_version(version: str) -> None:
    try:
        from packaging.version import Version, InvalidVersion  # type: ignore
    except Exception:
        return
    try:
        Version(version)
    except InvalidVersion as exc:
        raise HTTPException(status_code=400, detail="Invalid package version.") from exc


def _read_manifest(archive_bytes: bytes) -> dict:
    try:
        with zipfile.ZipFile(io.BytesIO(archive_bytes)) as zip_file:
            names = {info.filename for info in zip_file.infolist() if not info.is_dir()}
            if "manifest.json" not in names:
                raise HTTPException(status_code=400, detail="manifest.json must exist at the archive root.")
            with zip_file.open("manifest.json") as handle:
                payload = json.load(handle)
    except zipfile.BadZipFile as exc:
        raise HTTPException(status_code=400, detail="Invalid package archive.") from exc
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid manifest.json content.") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Invalid manifest.json content.")
    return payload


def _actor_display_name(actor_id: str) -> str:
    record = get_account(actor_id) or {}
    return record.get("displayName") or record.get("username") or actor_id


def _ensure_token_package(name: str) -> None:
    token_value = get_current_token_value()
    if not token_value:
        return
    token_record = get_token_record(token_value)
    if not token_record:
        return
    package_name = token_record.get("packageName")
    if package_name and _normalize(package_name) != _normalize(name):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


def _require_package_role(package_name: str, actor_id: str, required_role: str) -> str:
    if is_admin():
        return "admin"
    role = get_package_role_for_user(package_name, actor_id)
    if role is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    if _ROLE_RANK.get(role, 0) < _ROLE_RANK.get(required_role, 0):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return role


def _can_view_package(record: dict, actor_id: str | None) -> bool:
    visibility = record.get("visibility") or DEFAULT_VISIBILITY
    if visibility == "public":
        return True
    if is_admin():
        return True
    if not actor_id:
        return False
    if visibility == "internal":
        return True
    return get_package_role_for_user(record.get("name", ""), actor_id) is not None


def _require_package_access(record: dict | None, actor_id: str | None) -> dict:
    if not record:
        raise HTTPException(status_code=404, detail="Not Found")
    if _can_view_package(record, actor_id):
        return record
    raise HTTPException(status_code=404, detail="Not Found")


def _permission_from_record(record: dict) -> PackagePermission:
    payload = {
        "id": record.get("id"),
        "packageName": record.get("packageName"),
        "subjectType": record.get("subjectType"),
        "subjectId": record.get("subjectId"),
        "role": record.get("role"),
        "createdAt": record.get("createdAt"),
    }
    return PackagePermission.from_dict(payload)


class PackagesService:
    async def list_packages(
        self,
        q: str | None,
        tag: str | None,
        owner: str | None,
        page: int | None,
        page_size: int | None,
    ) -> PackageListResponse:
        query = _normalize(q)
        tag_value = _normalize(tag)
        owner_value = _normalize(owner)
        page_value = page or 1
        size_value = page_size or 20

        actor_id = get_current_actor()
        records = [
            record for record in list_packages() if _can_view_package(record, actor_id)
        ]
        filtered = [
            record
            for record in records
            if _match_query(record, query)
            and _match_tag(record, tag_value)
            and _match_owner(record, owner_value)
        ]
        fallback_time = datetime.min.replace(tzinfo=timezone.utc)
        filtered.sort(key=lambda item: item.get("updatedAt") or fallback_time, reverse=True)
        page_items, meta = _paginate(filtered, page_value, size_value)
        summaries = [_summary_from_record(record) for record in page_items]
        return PackageListResponse(items=summaries, meta=meta)

    async def publish_package(
        self,
        file: UploadFile,
        visibility: Visibility | None,
        summary: str | None,
        readme: str | None,
        tags: list[str] | None,
    ) -> PackageVersionDetail:
        actor_id = require_actor()
        if file is None:
            raise HTTPException(status_code=400, detail="Package archive is required.")
        archive_bytes = await file.read()
        if not archive_bytes:
            raise HTTPException(status_code=400, detail="Package archive is required.")
        manifest = _read_manifest(archive_bytes)
        name = manifest.get("name")
        version = manifest.get("version")
        if not isinstance(name, str) or not isinstance(version, str):
            raise HTTPException(status_code=400, detail="Manifest must include name and version.")
        if not name.strip() or not version.strip():
            raise HTTPException(status_code=400, detail="Manifest must include name and version.")
        _ensure_valid_version(version)
        _ensure_token_package(name)
        description = summary or manifest.get("description")
        if not isinstance(description, str):
            description = None
        readme_value = readme if isinstance(readme, str) and readme else manifest.get("readme")
        if not isinstance(readme_value, str):
            readme_value = None
        tag_values = _normalize_tags(tags)
        if tag_values is None:
            manifest_tags = manifest.get("tags")
            tag_values = _normalize_tags(manifest_tags)

        sha256 = hashlib.sha256(archive_bytes).hexdigest()
        size_bytes = len(archive_bytes)
        visibility_value = _visibility_value(visibility)

        record = get_package_record(name)
        if record:
            _require_package_role(name, actor_id, "maintainer")
            owner_id = record.get("ownerId")
            owner_name = record.get("ownerName")
        else:
            owner_id = actor_id
            owner_name = _actor_display_name(actor_id)

        try:
            _, version_record = publish_package_version(
                name=name,
                version=version,
                description=description,
                readme=readme_value,
                tags=tag_values,
                visibility=visibility_value,
                owner_id=owner_id,
                owner_name=owner_name,
                publisher_id=actor_id,
                archive_bytes=archive_bytes,
                archive_sha256=sha256,
                archive_size_bytes=size_bytes,
            )
        except ValueError as exc:
            if str(exc) == "package_version_exists":
                raise HTTPException(status_code=409, detail="Package version already exists.") from exc
            if str(exc) == "package_owner_mismatch":
                raise HTTPException(status_code=403, detail="Package ownership conflict.") from exc
            raise HTTPException(status_code=400, detail="Unable to publish package.") from exc
        record_audit_event(
            action="package.publish",
            actor_id=actor_id,
            target_type="package",
            target_id=name,
            metadata={
                "version": version,
                "visibility": visibility_value,
            },
        )
        return _version_detail_from_record(version_record)

    async def get_package(
        self,
        name: str,
    ) -> HubPackageDetail:
        record = _require_package_access(get_package_record(name), get_current_actor())
        return _detail_from_record(record)

    async def reserve_package(
        self,
        name: str,
        package_reserve_request: PackageReserveRequest | None,
    ) -> PackageRegistry:
        actor_id = require_actor()
        _ensure_token_package(name)
        record = get_package_record(name)
        if record:
            _require_package_role(name, actor_id, "owner")
            return _registry_from_record(record)
        visibility_value = DEFAULT_VISIBILITY
        if package_reserve_request and package_reserve_request.visibility:
            visibility_value = _visibility_value(package_reserve_request.visibility)
        record = reserve_package_record(
            name=name,
            owner_id=actor_id,
            owner_name=_actor_display_name(actor_id),
            visibility=visibility_value,
        )
        return _registry_from_record(record)

    async def get_package_version(
        self,
        name: str,
        version: str,
    ) -> PackageVersionDetail:
        record = _require_package_access(get_package_record(name), get_current_actor())
        version_record = record.get("versions", {}).get(version)
        if version_record is None:
            raise HTTPException(status_code=404, detail="Not Found")
        return _version_detail_from_record(version_record)

    async def download_package_archive(
        self,
        name: str,
        version: str | None,
    ) -> Response:
        record = _require_package_access(get_package_record(name), get_current_actor())
        version_value = version or record.get("latestVersion")
        if not version_value:
            raise HTTPException(status_code=404, detail="Not Found")
        version_record = get_package_version_record(name, version_value)
        archive_path_value = version_record.get("archivePath") if version_record else None
        if not archive_path_value:
            raise HTTPException(status_code=404, detail="Not Found")
        archive_path = resolve_storage_path(str(archive_path_value))
        if not archive_path.is_file():
            raise HTTPException(status_code=404, detail="Not Found")
        filename = f"{record.get('name')}-{version_value}.zip"
        return Response(
            content=archive_path.read_bytes(),
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    async def set_package_tag(
        self,
        name: str,
        tag: str,
        package_tag_request: PackageTagRequest,
    ) -> None:
        actor_id = require_actor()
        _ensure_token_package(name)
        _require_package_role(name, actor_id, "owner")
        if package_tag_request is None or not package_tag_request.version:
            raise HTTPException(status_code=400, detail="Tag version is required.")
        record = get_package_record(name) or {}
        prev_version = (record.get("distTags") or {}).get(tag)
        try:
            set_package_tag_record(name, tag, package_tag_request.version)
        except ValueError as exc:
            if str(exc) == "package_version_not_found":
                raise HTTPException(status_code=404, detail="Not Found") from exc
            raise HTTPException(status_code=404, detail="Not Found") from exc
        record_audit_event(
            action="package.tag.set",
            actor_id=actor_id,
            target_type="package",
            target_id=name,
            metadata={
                "tag": tag,
                "version": package_tag_request.version,
                "previousVersion": prev_version,
            },
        )
        return None

    async def delete_package_tag(
        self,
        name: str,
        tag: str,
    ) -> None:
        actor_id = require_actor()
        _ensure_token_package(name)
        _require_package_role(name, actor_id, "owner")
        record = get_package_record(name) or {}
        prev_version = (record.get("distTags") or {}).get(tag)
        try:
            delete_package_tag_record(name, tag)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail="Not Found") from exc
        record_audit_event(
            action="package.tag.delete",
            actor_id=actor_id,
            target_type="package",
            target_id=name,
            metadata={
                "tag": tag,
                "previousVersion": prev_version,
            },
        )
        return None

    async def update_package_visibility(
        self,
        name: str,
        package_visibility_request: PackageVisibilityRequest,
    ) -> PackageRegistry:
        actor_id = require_actor()
        _ensure_token_package(name)
        _require_package_role(name, actor_id, "owner")
        if package_visibility_request is None or not package_visibility_request.visibility:
            raise HTTPException(status_code=400, detail="Visibility is required.")
        try:
            record = update_package_visibility_record(
                name,
                _visibility_value(package_visibility_request.visibility),
            )
        except ValueError as exc:
            raise HTTPException(status_code=404, detail="Not Found") from exc
        record_audit_event(
            action="package.visibility.update",
            actor_id=actor_id,
            target_type="package",
            target_id=name,
            metadata={
                "visibility": record.get("visibility"),
            },
        )
        return _registry_from_record(record)

    async def transfer_package(
        self,
        name: str,
        package_transfer_request: PackageTransferRequest,
    ) -> PackageRegistry:
        actor_id = require_actor()
        _ensure_token_package(name)
        _require_package_role(name, actor_id, "owner")
        if package_transfer_request is None or not package_transfer_request.new_owner_id:
            raise HTTPException(status_code=400, detail="newOwnerId is required.")
        new_owner_id = package_transfer_request.new_owner_id
        new_owner_name = _actor_display_name(new_owner_id)
        try:
            record = transfer_package_record(
                name,
                new_owner_id,
                new_owner_name,
            )
        except ValueError as exc:
            raise HTTPException(status_code=404, detail="Not Found") from exc
        permissions = list_package_permissions(name)
        if not any(
            perm.get("subjectType") == "user"
            and perm.get("subjectId") == new_owner_id
            and perm.get("role") == "owner"
            for perm in permissions
        ):
            add_package_permission(
                package_name=name,
                subject_type="user",
                subject_id=new_owner_id,
                role="owner",
            )
        record_audit_event(
            action="package.transfer",
            actor_id=actor_id,
            target_type="package",
            target_id=name,
            metadata={
                "newOwnerId": new_owner_id,
                "newOwnerName": new_owner_name,
            },
        )
        return _registry_from_record(record)

    async def list_package_permissions(
        self,
        name: str,
    ) -> PackagePermissionList:
        actor_id = require_actor()
        _ensure_token_package(name)
        if not get_package_record(name):
            raise HTTPException(status_code=404, detail="Not Found")
        _require_package_role(name, actor_id, "owner")
        permissions = [
            _permission_from_record(record)
            for record in list_package_permissions(name)
        ]
        return PackagePermissionList(items=permissions)

    async def add_package_permission(
        self,
        name: str,
        package_permission_create_request: PackagePermissionCreateRequest,
    ) -> PackagePermission:
        actor_id = require_actor()
        _ensure_token_package(name)
        if not get_package_record(name):
            raise HTTPException(status_code=404, detail="Not Found")
        _require_package_role(name, actor_id, "owner")
        if package_permission_create_request is None:
            raise HTTPException(status_code=400, detail="Payload is required.")
        permission = add_package_permission(
            package_name=name,
            subject_type=_enum_value(package_permission_create_request.subject_type),
            subject_id=package_permission_create_request.subject_id,
            role=_enum_value(package_permission_create_request.role),
        )
        record_audit_event(
            action="package.permission.add",
            actor_id=actor_id,
            target_type="package",
            target_id=name,
            metadata={
                "permissionId": permission.get("id"),
                "subjectType": permission.get("subjectType"),
                "subjectId": permission.get("subjectId"),
                "role": permission.get("role"),
            },
        )
        return _permission_from_record(permission)

    async def delete_package_permission(
        self,
        name: str,
        permissionId: str,
    ) -> None:
        actor_id = require_actor()
        _ensure_token_package(name)
        if not get_package_record(name):
            raise HTTPException(status_code=404, detail="Not Found")
        _require_package_role(name, actor_id, "owner")
        permissions = list_package_permissions(name)
        permission_record = next(
            (permission for permission in permissions if permission.get("id") == permissionId),
            None,
        )
        if not permission_record:
            raise HTTPException(status_code=404, detail="Not Found")
        delete_package_permission(permissionId)
        record_audit_event(
            action="package.permission.remove",
            actor_id=actor_id,
            target_type="package",
            target_id=name,
            metadata={
                "permissionId": permissionId,
                "subjectType": permission_record.get("subjectType"),
                "subjectId": permission_record.get("subjectId"),
                "role": permission_record.get("role"),
            },
        )
        return None

    async def update_package_permission(
        self,
        name: str,
        permissionId: str,
        package_permission_update_request: PackagePermissionUpdateRequest,
    ) -> PackagePermission:
        actor_id = require_actor()
        _ensure_token_package(name)
        if not get_package_record(name):
            raise HTTPException(status_code=404, detail="Not Found")
        _require_package_role(name, actor_id, "owner")
        if package_permission_update_request is None:
            raise HTTPException(status_code=400, detail="Payload is required.")
        permissions = list_package_permissions(name)
        if not any(permission.get("id") == permissionId for permission in permissions):
            raise HTTPException(status_code=404, detail="Not Found")
        try:
            permission = update_package_permission(
                permissionId,
                _enum_value(package_permission_update_request.role),
            )
        except ValueError as exc:
            raise HTTPException(status_code=404, detail="Not Found") from exc
        record_audit_event(
            action="package.permission.update",
            actor_id=actor_id,
            target_type="package",
            target_id=name,
            metadata={
                "permissionId": permission.get("id"),
                "subjectType": permission.get("subjectType"),
                "subjectId": permission.get("subjectId"),
                "role": permission.get("role"),
            },
        )
        return _permission_from_record(permission)
