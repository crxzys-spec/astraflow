"""HTTP client for AstraFlow Hub APIs."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, BinaryIO, Iterable
from urllib.parse import urlencode, urljoin

import requests
from requests import Response

from scheduler_api.config.settings import get_api_settings


class HubClientError(Exception):
    """Base error for Hub client operations."""


class HubNotConfiguredError(HubClientError):
    """Raised when Hub settings are missing."""


class HubNotFoundError(HubClientError):
    """Raised when the Hub returns 404."""


class HubUnauthorizedError(HubClientError):
    """Raised when Hub authentication fails."""


class HubConflictError(HubClientError):
    """Raised when Hub returns a conflict."""


class HubRequestError(HubClientError):
    """Raised for unexpected Hub failures."""


@dataclass(frozen=True)
class HubDownloadResult:
    path: Path
    size_bytes: int


class HubClient:
    def __init__(
        self,
        *,
        base_url: str,
        service_token: str | None,
        timeout_seconds: int,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._service_token = service_token
        self._timeout_seconds = timeout_seconds

    @classmethod
    def from_settings(cls) -> HubClient:
        settings = get_api_settings()
        if not settings.hub_base_url:
            raise HubNotConfiguredError("Hub base URL is not configured.")
        return cls(
            base_url=settings.hub_base_url,
            service_token=settings.hub_service_token,
            timeout_seconds=int(settings.hub_timeout_seconds),
        )

    def list_packages(
        self,
        *,
        query: str | None,
        tag: str | None,
        owner: str | None,
        page: int | None,
        page_size: int | None,
    ) -> dict[str, Any]:
        params = {
            "q": query,
            "tag": tag,
            "owner": owner,
            "page": page,
            "pageSize": page_size,
        }
        return self._request_json("GET", "/api/v1/packages", params=params)

    def get_package(self, name: str) -> dict[str, Any]:
        return self._request_json("GET", f"/api/v1/packages/{name}")

    def get_package_version(self, name: str, version: str) -> dict[str, Any]:
        return self._request_json("GET", f"/api/v1/packages/{name}/versions/{version}")

    def publish_package(
        self,
        *,
        file_obj: BinaryIO,
        filename: str,
        visibility: str | None,
        summary: str | None,
        readme: str | None,
        tags: Iterable[str] | None,
    ) -> dict[str, Any]:
        data: dict[str, Any] = {}
        if visibility:
            data["visibility"] = visibility
        if summary:
            data["summary"] = summary
        if readme:
            data["readme"] = readme
        if tags:
            data["tags"] = list(tags)
        files = {"file": (filename, file_obj, "application/zip")}
        return self._request_json("POST", "/api/v1/packages", data=data, files=files)

    def download_package_archive(
        self,
        name: str,
        *,
        version: str | None,
        dest_path: Path | None = None,
    ) -> HubDownloadResult | bytes:
        params = {"version": version} if version else None
        response = self._request("GET", f"/api/v1/packages/{name}/archive", params=params, stream=True)
        if dest_path is None:
            return response.content
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        size_bytes = 0
        with dest_path.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if not chunk:
                    continue
                handle.write(chunk)
                size_bytes += len(chunk)
        return HubDownloadResult(path=dest_path, size_bytes=size_bytes)

    def list_workflows(
        self,
        *,
        query: str | None,
        tag: str | None,
        owner: str | None,
        page: int | None,
        page_size: int | None,
    ) -> dict[str, Any]:
        params = {
            "q": query,
            "tag": tag,
            "owner": owner,
            "page": page,
            "pageSize": page_size,
        }
        return self._request_json("GET", "/api/v1/workflows", params=params)

    def get_workflow(self, workflow_id: str) -> dict[str, Any]:
        return self._request_json("GET", f"/api/v1/workflows/{workflow_id}")

    def list_workflow_versions(self, workflow_id: str) -> dict[str, Any]:
        return self._request_json("GET", f"/api/v1/workflows/{workflow_id}/versions")

    def get_workflow_version(self, workflow_id: str, version_id: str) -> dict[str, Any]:
        return self._request_json(
            "GET",
            f"/api/v1/workflows/{workflow_id}/versions/{version_id}",
        )

    def get_workflow_definition(self, workflow_id: str, version_id: str) -> dict[str, Any]:
        return self._request_json(
            "GET",
            f"/api/v1/workflows/{workflow_id}/versions/{version_id}/definition",
        )

    def publish_workflow(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request_json("POST", "/api/v1/workflows", json_body=payload)

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, object] | None = None,
        json_body: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        files: dict[str, tuple[str, BinaryIO, str]] | None = None,
    ) -> dict[str, Any]:
        response = self._request(
            method,
            path,
            params=params,
            json_body=json_body,
            data=data,
            files=files,
            stream=False,
        )
        if not response.content:
            return {}
        try:
            return response.json()
        except json.JSONDecodeError as exc:
            raise HubRequestError("Hub returned invalid JSON.") from exc

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, object] | None = None,
        json_body: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        files: dict[str, tuple[str, BinaryIO, str]] | None = None,
        stream: bool,
    ) -> Response:
        url = self._build_url(path, params=params)
        try:
            response = requests.request(
                method,
                url,
                headers=self._build_headers(),
                json=json_body,
                data=data,
                files=files,
                timeout=self._timeout_seconds,
                stream=stream,
            )
        except requests.RequestException as exc:
            raise HubRequestError(str(exc)) from exc
        if response.status_code >= 400:
            self._raise_for_status(response)
        return response

    def _build_headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self._service_token:
            headers["Authorization"] = f"Bearer {self._service_token}"
        return headers

    def _build_url(self, path: str, *, params: dict[str, object] | None = None) -> str:
        url = urljoin(f"{self._base_url}/", path.lstrip("/"))
        if params:
            query = urlencode({key: value for key, value in params.items() if value is not None})
            if query:
                return f"{url}?{query}"
        return url

    @staticmethod
    def _raise_for_status(response: Response) -> None:
        if response.status_code == 404:
            raise HubNotFoundError("Hub resource not found.")
        if response.status_code in {401, 403}:
            raise HubUnauthorizedError("Hub access denied.")
        if response.status_code == 409:
            raise HubConflictError("Hub resource conflict.")
        raise HubRequestError(f"Hub request failed with status {response.status_code}.")


__all__ = [
    "HubClient",
    "HubClientError",
    "HubNotConfiguredError",
    "HubNotFoundError",
    "HubUnauthorizedError",
    "HubConflictError",
    "HubRequestError",
    "HubDownloadResult",
]
