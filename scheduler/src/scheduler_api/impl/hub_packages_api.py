from __future__ import annotations

from fastapi import UploadFile
from fastapi.responses import Response

from scheduler_api.apis.hub_packages_api_base import BaseHubPackagesApi
from scheduler_api.auth.roles import WORKFLOW_EDIT_ROLES, WORKFLOW_VIEW_ROLES, require_roles
from scheduler_api.http.errors import bad_request, conflict, forbidden, not_found
from scheduler_api.infra.catalog.package_catalog import _version_key
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
        try:
            file.file.seek(0)
            payload = HubClient.from_settings().publish_package(
                file_obj=file.file,
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
        return HubPackageVersionDetail.from_dict(payload)

    async def get_hub_package(self, packageName: str) -> HubPackageDetail:
        require_roles(*WORKFLOW_VIEW_ROLES)
        try:
            payload = HubClient.from_settings().get_package(packageName)
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
        packageName: str,
        version: str,
    ) -> HubPackageVersionDetail:
        require_roles(*WORKFLOW_VIEW_ROLES)
        try:
            payload = HubClient.from_settings().get_package_version(packageName, version)
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
        packageName: str,
        version: str | None,
    ) -> Response:
        require_roles(*WORKFLOW_VIEW_ROLES)
        try:
            content = HubClient.from_settings().download_package_archive(
                packageName,
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
        packageName: str,
        hub_package_install_request: HubPackageInstallRequest | None,
    ) -> HubPackageInstallResponse:
        require_roles(*WORKFLOW_EDIT_ROLES)
        version_value = None
        if hub_package_install_request and hub_package_install_request.version:
            version_value = hub_package_install_request.version
        if not version_value:
            try:
                detail = HubClient.from_settings().get_package(packageName)
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
            hub_mirror_service.ensure_package(name=packageName, version=version_value)
            hub_mirror_service.install_to_catalog(name=packageName, version=version_value)
        except HubMirrorError as exc:
            raise bad_request(str(exc), error="hub_install_failed") from exc

        return HubPackageInstallResponse(
            name=packageName,
            version=version_value,
            installed=True,
        )
