"""HTTP client for external registry APIs."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urljoin
from urllib.request import Request, urlopen

from scheduler_api.config.settings import get_api_settings


class RegistryClientError(Exception):
    """Base error for registry client operations."""


class RegistryNotConfiguredError(RegistryClientError):
    """Raised when registry settings are missing."""


class RegistryNotFoundError(RegistryClientError):
    """Raised when the registry returns 404."""


class RegistryUnauthorizedError(RegistryClientError):
    """Raised when registry authentication fails."""


class RegistryRequestError(RegistryClientError):
    """Raised for unexpected registry failures."""


@dataclass(frozen=True)
class RegistryActor:
    platform_user_id: str | None
    registry_user_id: str | None
    registry_username: str | None


class RegistryClient:
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
    def from_settings(cls) -> RegistryClient:
        settings = get_api_settings()
        if not settings.registry_base_url:
            raise RegistryNotConfiguredError("Registry base URL is not configured.")
        return cls(
            base_url=settings.registry_base_url,
            service_token=settings.registry_service_token,
            timeout_seconds=int(settings.registry_timeout_seconds),
        )

    def get_package_detail(
        self,
        name: str,
        *,
        version: str | None,
        actor: RegistryActor | None,
    ) -> dict[str, Any]:
        params = {"version": version} if version else None
        return self._request_json(
            "GET",
            f"/api/v1/published-packages/{name}",
            params=params,
            actor=actor,
        )

    def download_package_archive(
        self,
        name: str,
        *,
        version: str,
        dest_path: Path,
        actor: RegistryActor | None,
    ) -> str | None:
        params = {"version": version}
        url = self._build_url(f"/api/v1/published-packages/{name}/archive", params=params)
        request = Request(url, method="GET", headers=self._build_headers(actor))
        try:
            with urlopen(request, timeout=self._timeout_seconds) as response:
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                with dest_path.open("wb") as handle:
                    handle.write(response.read())
                return response.headers.get("X-Package-Archive-Sha256")
        except HTTPError as exc:
            self._raise_for_status(exc)
        except URLError as exc:
            raise RegistryRequestError(str(exc)) from exc
        return None

    def get_workflow_package(
        self,
        package_id: str,
        *,
        actor: RegistryActor | None,
    ) -> dict[str, Any]:
        return self._request_json(
            "GET",
            f"/api/v1/workflow-packages/{package_id}",
            actor=actor,
        )

    def get_workflow_definition(
        self,
        package_id: str,
        *,
        version_id: str,
        actor: RegistryActor | None,
    ) -> dict[str, Any]:
        return self._request_json(
            "GET",
            f"/api/v1/workflow-packages/{package_id}/versions/{version_id}/definition",
            actor=actor,
        )

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, str] | None = None,
        actor: RegistryActor | None = None,
    ) -> dict[str, Any]:
        url = self._build_url(path, params=params)
        request = Request(url, method=method, headers=self._build_headers(actor))
        try:
            with urlopen(request, timeout=self._timeout_seconds) as response:
                payload = response.read().decode("utf-8")
                if not payload:
                    return {}
                return json.loads(payload)
        except HTTPError as exc:
            self._raise_for_status(exc)
        except URLError as exc:
            raise RegistryRequestError(str(exc)) from exc
        except json.JSONDecodeError as exc:
            raise RegistryRequestError("Registry returned invalid JSON.") from exc
        return {}

    def _build_headers(self, actor: RegistryActor | None) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self._service_token:
            headers["Authorization"] = f"Bearer {self._service_token}"
        if actor:
            if actor.registry_user_id:
                headers["X-Registry-Actor-Id"] = actor.registry_user_id
            if actor.registry_username:
                headers["X-Registry-Actor-Name"] = actor.registry_username
            if actor.platform_user_id:
                headers["X-Platform-Actor-Id"] = actor.platform_user_id
        return headers

    def _build_url(self, path: str, *, params: dict[str, str] | None = None) -> str:
        url = urljoin(f"{self._base_url}/", path.lstrip("/"))
        if params:
            query = urlencode({key: value for key, value in params.items() if value is not None})
            if query:
                return f"{url}?{query}"
        return url

    @staticmethod
    def _raise_for_status(exc: HTTPError) -> None:
        if exc.code == 404:
            raise RegistryNotFoundError("Registry resource not found.") from exc
        if exc.code in {401, 403}:
            raise RegistryUnauthorizedError("Registry access denied.") from exc
        raise RegistryRequestError(f"Registry request failed with status {exc.code}.") from exc


__all__ = [
    "RegistryActor",
    "RegistryClient",
    "RegistryClientError",
    "RegistryNotConfiguredError",
    "RegistryNotFoundError",
    "RegistryUnauthorizedError",
    "RegistryRequestError",
]
