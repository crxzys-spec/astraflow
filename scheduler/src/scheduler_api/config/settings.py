"""Scheduler configuration using pydantic-settings."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import ClassVar, Literal, Set

from pydantic import AliasChoices, Field, NonNegativeInt, PositiveInt
from pydantic_settings import BaseSettings, SettingsConfigDict


class SchedulerApiSettings(BaseSettings):
    """Process/runtime settings for the scheduler API server."""

    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_prefix="SCHEDULER_API_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    host: str = Field(default="127.0.0.1", description="Bind address for the scheduler API.")
    port: PositiveInt = Field(default=8080, description="Port for the scheduler API.")
    reload: bool = Field(default=False, description="Enable uvicorn auto-reload (dev only).")
    log_level: Literal["critical", "error", "warning", "info", "debug", "trace"] = Field(
        default="info",
        description="Log level for scheduler API / uvicorn.",
    )
    public_base_url: str | None = Field(
        default=None,
        description="Optional public base URL used to build absolute links.",
    )
    resource_provider: str = Field(
        default="local",
        description="Default resource storage provider.",
    )
    resource_providers: list[str] = Field(
        default_factory=lambda: ["local", "db"],
        description="Allowed resource storage providers.",
    )
    resource_dir: Path = Field(
        default=Path(__file__).resolve().parents[4] / "scheduler" / "data" / "resources",
        description="Local directory used for uploaded resources.",
    )
    packages_root: Path = Field(
        default=Path(__file__).resolve().parents[4] / "node-packages",
        validation_alias=AliasChoices("SCHEDULER_API_PACKAGES_ROOT", "ASTRA_PACKAGES_ROOT"),
        description="Root directory where runtime node packages are stored.",
    )
    published_packages_root: Path = Field(
        default=Path(__file__).resolve().parents[4] / "var" / "packages",
        validation_alias=AliasChoices(
            "SCHEDULER_API_PUBLISHED_PACKAGES_ROOT",
            "ASTRA_PUBLISHED_PACKAGES_ROOT",
        ),
        description="Root directory where published package archives are stored.",
    )
    published_packages_max_owner_bytes: NonNegativeInt = Field(
        default=0,
        description="Max total bytes per owner across published packages (0 = unlimited).",
    )
    published_packages_max_package_bytes: NonNegativeInt = Field(
        default=0,
        description="Max total bytes per package across versions (0 = unlimited).",
    )
    published_packages_max_versions_per_package: NonNegativeInt = Field(
        default=0,
        description="Max versions retained per package (0 = unlimited).",
    )
    registry_base_url: str | None = Field(
        default=None,
        description="Base URL for the external registry service.",
    )
    registry_service_token: str | None = Field(
        default=None,
        description="Service token used for registry API access.",
    )
    registry_timeout_seconds: PositiveInt = Field(
        default=30,
        description="Registry HTTP client timeout (seconds).",
    )
    registry_workflow_pull_policy: Literal["auto", "admin_approval", "whitelist"] = Field(
        default="auto",
        description="Policy for pulling workflows from registry.",
    )
    registry_package_pull_policy: Literal["auto", "admin_approval", "whitelist"] = Field(
        default="auto",
        description="Policy for pulling node packages from registry.",
    )
    registry_publish_dependency_policy: Literal["block", "auto_publish"] = Field(
        default="block",
        description="Policy for missing package dependencies during workflow publish.",
    )
    registry_mirror_root: Path = Field(
        default=Path(__file__).resolve().parents[4] / "var" / "registry-packages",
        description="Local cache root for mirrored registry package archives.",
    )
    hub_base_url: str | None = Field(
        default=None,
        description="Base URL for the AstraFlow Hub service.",
    )
    hub_service_token: str | None = Field(
        default=None,
        description="Service token used for Hub API access.",
    )
    hub_timeout_seconds: PositiveInt = Field(
        default=30,
        description="Hub HTTP client timeout (seconds).",
    )
    hub_workflow_pull_policy: Literal["auto", "admin_approval", "whitelist"] = Field(
        default="auto",
        description="Policy for pulling workflows from Hub.",
    )
    hub_package_pull_policy: Literal["auto", "admin_approval", "whitelist"] = Field(
        default="auto",
        description="Policy for pulling node packages from Hub.",
    )
    hub_publish_dependency_policy: Literal["block", "auto_publish"] = Field(
        default="block",
        description="Policy for missing package dependencies during Hub workflow publish.",
    )
    hub_mirror_root: Path = Field(
        default=Path(__file__).resolve().parents[4] / "var" / "hub-packages",
        description="Local cache root for Hub package archives.",
    )
    resource_upload_ttl_seconds: NonNegativeInt = Field(
        default=86400,
        description="TTL for upload sessions in seconds (0 disables cleanup).",
    )


class SchedulerSettings(BaseSettings):
    """Validated settings for the scheduler control-plane."""

    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_prefix="ASTRA_SCHEDULER_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    worker_token: str | None = Field(
        default=None,
        description="Single worker token allowed for control-plane handshake.",
    )
    worker_tokens: list[str] = Field(
        default_factory=list,
        description="List of allowed worker tokens for control-plane handshake.",
    )
    session_secret: str = Field(
        default="dev-session-secret",
        description="Secret used to sign/verify session tokens.",
    )
    session_token_ttl_seconds: PositiveInt = Field(
        default=3600,
        description="TTL for issued session tokens (seconds).",
    )
    session_window_size: PositiveInt = Field(
        default=64,
        description="Sliding window size for session sequencing/ack bitmaps.",
    )
    dispatch_worker_strategy: str = Field(
        default="default",
        description="Worker selection strategy for dispatch (default, least_inflight, least_latency, random).",
    )
    dispatch_worker_max_heartbeat_age_seconds: PositiveInt = Field(
        default=90,
        description="Max heartbeat age (seconds) for eligible workers.",
    )

    def allowed_worker_tokens(self) -> Set[str]:
        tokens: Set[str] = set()
        if self.worker_token:
            tokens.add(self.worker_token.strip())
        tokens.update(token.strip() for token in self.worker_tokens if token)
        return {t for t in tokens if t}


@lru_cache()
def get_settings() -> SchedulerSettings:
    """Return memoized scheduler settings."""

    return SchedulerSettings()


@lru_cache()
def get_api_settings() -> SchedulerApiSettings:
    """Return memoized API process settings."""

    return SchedulerApiSettings()
