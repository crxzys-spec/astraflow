"""Shared error helpers for HTTP APIs."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import HTTPException, status

from scheduler_api.models.error import Error

_STATUS_ERROR_CODES: dict[int, str] = {
    status.HTTP_400_BAD_REQUEST: "bad_request",
    status.HTTP_401_UNAUTHORIZED: "unauthorized",
    status.HTTP_403_FORBIDDEN: "forbidden",
    status.HTTP_404_NOT_FOUND: "not_found",
    status.HTTP_409_CONFLICT: "conflict",
    status.HTTP_500_INTERNAL_SERVER_ERROR: "internal_error",
}


def error_payload(
    message: str,
    *,
    error: Optional[str] = None,
    status_code: Optional[int] = None,
    details: Optional[dict[str, Any]] = None,
    request_id: Optional[str] = None,
) -> dict[str, Any]:
    resolved_error = error or _STATUS_ERROR_CODES.get(status_code or 0, "error")
    return Error(
        error=resolved_error,
        message=message,
        request_id=request_id,
        details=details,
    ).model_dump(by_alias=True, exclude_none=True)


def http_error(
    status_code: int,
    message: str,
    *,
    error: Optional[str] = None,
    details: Optional[dict[str, Any]] = None,
    request_id: Optional[str] = None,
) -> HTTPException:
    payload = error_payload(
        message,
        error=error,
        status_code=status_code,
        details=details,
        request_id=request_id,
    )
    return HTTPException(status_code=status_code, detail=payload)


def bad_request(
    message: str,
    *,
    error: Optional[str] = None,
    details: Optional[dict[str, Any]] = None,
) -> HTTPException:
    return http_error(
        status.HTTP_400_BAD_REQUEST,
        message,
        error=error,
        details=details,
    )


def unauthorized(
    message: str,
    *,
    error: Optional[str] = None,
    details: Optional[dict[str, Any]] = None,
) -> HTTPException:
    return http_error(
        status.HTTP_401_UNAUTHORIZED,
        message,
        error=error,
        details=details,
    )


def forbidden(
    message: str,
    *,
    error: Optional[str] = None,
    details: Optional[dict[str, Any]] = None,
) -> HTTPException:
    return http_error(
        status.HTTP_403_FORBIDDEN,
        message,
        error=error,
        details=details,
    )


def not_found(
    message: str,
    *,
    error: Optional[str] = None,
    details: Optional[dict[str, Any]] = None,
) -> HTTPException:
    return http_error(
        status.HTTP_404_NOT_FOUND,
        message,
        error=error,
        details=details,
    )


def conflict(
    message: str,
    *,
    error: Optional[str] = None,
    details: Optional[dict[str, Any]] = None,
) -> HTTPException:
    return http_error(
        status.HTTP_409_CONFLICT,
        message,
        error=error,
        details=details,
    )


def internal_error(
    message: str,
    *,
    error: Optional[str] = None,
    details: Optional[dict[str, Any]] = None,
) -> HTTPException:
    return http_error(
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        message,
        error=error,
        details=details,
    )


__all__ = [
    "bad_request",
    "conflict",
    "error_payload",
    "forbidden",
    "http_error",
    "internal_error",
    "not_found",
    "unauthorized",
]
