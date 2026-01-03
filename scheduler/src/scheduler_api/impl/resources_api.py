from __future__ import annotations

from typing import Optional

from fastapi import UploadFile
from fastapi.responses import FileResponse
from pydantic import StrictStr

from scheduler_api.apis.resources_api_base import BaseResourcesApi
from scheduler_api.auth.context import get_current_token
from scheduler_api.auth.roles import WORKFLOW_EDIT_ROLES, WORKFLOW_VIEW_ROLES, require_roles
from scheduler_api.models.resource import Resource
from scheduler_api.models.resource_list import ResourceList
from scheduler_api.models.resource_upload_init_request import ResourceUploadInitRequest
from scheduler_api.models.resource_upload_part import ResourceUploadPart
from scheduler_api.models.resource_upload_session import ResourceUploadSession
from scheduler_api.infra.resources import StoredResource
from scheduler_api.service.facade import resource_services
from scheduler_api.service.resources import (
    ResourceNotFoundError,
    UploadConflictError,
    UploadNotFoundError,
    UploadValidationError,
)


class ResourcesApiImpl(BaseResourcesApi):
    async def list_resources(
        self,
        limit: Optional[int],
        cursor: Optional[str],
        search: Optional[StrictStr],
        owner_id: Optional[StrictStr],
    ) -> ResourceList:
        del cursor  # cursor reserved for future pagination
        token = require_roles(*WORKFLOW_VIEW_ROLES)
        is_admin = "admin" in (token.roles if token else [])
        owner_filter = str(owner_id) if owner_id else None
        if owner_filter == "me" or not owner_filter:
            owner_filter = token.sub if token else None
        elif not is_admin and token and owner_filter != token.sub:
            raise forbidden("Insufficient role to view other users' resources.")
        resources = resource_services.resources.list_resources(
            owner_id=owner_filter,
            search=str(search) if search else None,
        )
        if limit:
            resources = resources[: max(0, int(limit))]
        return ResourceList(
            items=[_to_resource_model(item) for item in resources],
            next_cursor=None,
        )

    async def upload_resource(
        self,
        file: UploadFile,
        provider: Optional[StrictStr],
    ) -> Resource:
        require_roles(*WORKFLOW_EDIT_ROLES)
        token = get_current_token()
        owner_id = token.sub if token else None
        visibility = "private"
        if file is None:
            raise bad_request("Missing upload payload.")
        try:
            stored = await resource_services.resources.upload_resource(
                file=file,
                provider=str(provider) if provider is not None else None,
                owner_id=owner_id,
                visibility=visibility,
            )
        except ValueError as exc:
            raise bad_request(str(exc)) from exc
        return _to_resource_model(stored)

    async def create_resource_upload(
        self,
        resource_upload_init_request: ResourceUploadInitRequest,
    ) -> ResourceUploadSession:
        require_roles(*WORKFLOW_EDIT_ROLES)
        token = get_current_token()
        try:
            session = resource_services.resources.create_upload_session(
                request=resource_upload_init_request,
                owner_id=token.sub if token else None,
            )
        except UploadValidationError as exc:
            raise bad_request(str(exc), error="upload_validation_error") from exc
        except ValueError as exc:
            raise bad_request(str(exc)) from exc
        return ResourceUploadSession.from_dict(session.to_dict())

    async def get_resource_upload(self, uploadId: StrictStr) -> ResourceUploadSession:
        require_roles(*WORKFLOW_VIEW_ROLES)
        try:
            session = resource_services.resources.get_upload_session(str(uploadId))
        except UploadNotFoundError as exc:
            raise not_found(str(exc), error="upload_not_found") from exc
        return ResourceUploadSession.from_dict(session.to_dict())

    async def delete_resource_upload(self, uploadId: StrictStr) -> None:
        require_roles(*WORKFLOW_EDIT_ROLES)
        try:
            resource_services.resources.abort_upload_session(str(uploadId))
        except UploadNotFoundError as exc:
            raise not_found(str(exc), error="upload_not_found") from exc
        return None

    async def upload_resource_part(
        self,
        uploadId: StrictStr,
        partNumber: int,
        file: UploadFile,
    ) -> ResourceUploadPart:
        require_roles(*WORKFLOW_EDIT_ROLES)
        try:
            session, received_bytes = await resource_services.resources.write_upload_part(
                upload_id=str(uploadId),
                part_number=int(partNumber),
                file=file,
            )
        except UploadNotFoundError as exc:
            raise not_found(str(exc), error="upload_not_found") from exc
        except UploadConflictError as exc:
            raise conflict(f"Expected part {exc.expected_part}.", error="upload_conflict") from exc
        except UploadValidationError as exc:
            raise bad_request(str(exc), error="upload_validation_error") from exc
        except ValueError as exc:
            raise bad_request(str(exc)) from exc
        status_value = "completed" if session.uploaded_bytes >= session.size_bytes else "pending"
        return ResourceUploadPart.from_dict(
            {
                "uploadId": session.upload_id,
                "partNumber": partNumber,
                "receivedBytes": received_bytes,
                "uploadedBytes": session.uploaded_bytes,
                "nextPart": session.next_part,
                "status": status_value,
            }
        )

    async def complete_resource_upload(self, uploadId: StrictStr) -> Resource:
        require_roles(*WORKFLOW_EDIT_ROLES)
        try:
            stored = resource_services.resources.complete_upload(str(uploadId))
        except UploadNotFoundError as exc:
            raise not_found(str(exc), error="upload_not_found") from exc
        except UploadValidationError as exc:
            raise bad_request(str(exc), error="upload_validation_error") from exc
        except FileNotFoundError as exc:
            raise not_found(str(exc)) from exc
        except ResourceNotFoundError as exc:
            raise not_found(str(exc)) from exc
        return _to_resource_model(stored)

    async def get_resource(self, resourceId: StrictStr) -> Resource:
        require_roles(*WORKFLOW_VIEW_ROLES)
        try:
            stored = resource_services.resources.get_resource(str(resourceId))
        except ResourceNotFoundError as exc:
            raise not_found(str(exc)) from exc
        return _to_resource_model(stored)

    async def delete_resource(self, resourceId: StrictStr) -> None:
        require_roles(*WORKFLOW_EDIT_ROLES)
        try:
            resource_services.resources.get_resource(str(resourceId))
        except ResourceNotFoundError as exc:
            raise not_found(str(exc)) from exc
        resource_services.resources.delete_resource(str(resourceId))
        return None

    async def download_resource(self, resourceId: StrictStr) -> FileResponse:
        require_roles(*WORKFLOW_VIEW_ROLES)
        try:
            file_path, stored = resource_services.resources.open_resource(str(resourceId))
        except ResourceNotFoundError as exc:
            raise not_found(str(exc)) from exc
        media_type = stored.mime_type or "application/octet-stream"
        return FileResponse(
            path=file_path,
            media_type=media_type,
            filename=stored.filename or file_path.name,
        )


def _to_resource_model(stored: StoredResource) -> Resource:
    return Resource(
        resource_id=stored.resource_id,
        provider=stored.provider,
        type=stored.type,
        filename=stored.filename,
        owner_id=stored.owner_id,
        visibility=stored.visibility,
        mime_type=stored.mime_type,
        size_bytes=stored.size_bytes,
        sha256=stored.sha256,
        created_at=stored.created_at,
        expires_at=stored.expires_at,
        metadata=stored.metadata,
        download_url=f"/api/v1/resources/{stored.resource_id}/download",
    )
from scheduler_api.http.errors import bad_request, conflict, forbidden, not_found
