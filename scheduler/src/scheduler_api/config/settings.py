"""Scheduler configuration using pydantic-settings."""

from __future__ import annotations

from functools import lru_cache
from typing import ClassVar, Literal, Set

from pydantic import Field, PositiveInt
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
