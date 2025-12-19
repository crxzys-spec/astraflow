"""Worker configuration loading and validation."""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, ClassVar, Dict, Iterable, Literal

import yaml
from pydantic import AnyUrl, Field, PositiveInt
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_CONFIG_LOCATIONS: tuple[Path, ...] = (
    Path("/etc/astraflow/worker.yaml"),
    Path("/etc/astraflow/worker.yml"),
    Path("./config/worker.yaml"),
    Path("./config/worker.yml"),
)


def _default_packages_dir() -> Path:
    env_root = os.getenv("ASTRA_PACKAGES_ROOT")
    if env_root:
        return Path(env_root)
    return Path(__file__).resolve().parents[2] / "node-packages"


class WorkerSettings(BaseSettings):
    """Validated settings for the worker runtime."""

    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_prefix="ASTRA_WORKER_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Connection + identity
    scheduler_ws_url: AnyUrl = Field(
        default="ws://localhost:8080/ws/worker",
        description="Scheduler control-plane WebSocket endpoint.",
    )
    scheduler_rest_base_url: AnyUrl = Field(
        default="http://localhost:8080/api/v1",
        description="Scheduler REST base URL used for auxiliary requests.",
    )
    tenant: str = Field(
        default="default",
        description="Tenant identifier included in envelope headers.",
    )
    worker_name: str = Field(
        default="worker-local",
        description="Logical worker label presented to the scheduler.",
    )
    worker_instance_id: str | None = Field(
        default=None,
        description="Scheduler-issued immutable instance id used as sender.id.",
    )
    auth_token: str | None = Field(
        default=None,
        description="Bearer or opaque token attached during handshake/login.",
        repr=False,
    )
    worker_version: str = Field(
        default="0.1.0",
        description="Semantic version presented during handshake.",
    )
    handshake_protocol_version: PositiveInt = Field(
        default=1,
        description="Control-plane protocol version advertised in handshake.",
    )
    auth_mode: Literal["token", "mtls"] = Field(
        default="token",
        description="Authentication mode announced to the scheduler.",
    )
    auth_fingerprint: str | None = Field(
        default=None,
        description="Optional mTLS fingerprint provided when auth_mode=mtls.",
        repr=False,
    )
    transport: Literal["dummy", "websocket"] = Field(
        default="websocket",
        description="Control-plane transport implementation to use.",
    )

    # Heartbeat & reliability
    heartbeat_interval_seconds: PositiveInt = Field(
        default=30,
        description="Nominal heartbeat frequency to the scheduler.",
    )
    heartbeat_jitter_seconds: PositiveInt = Field(
        default=5,
        description="Randomised jitter applied to heartbeat scheduling.",
    )
    ack_retry_base_ms: PositiveInt = Field(
        default=200,
        description="Base backoff (milliseconds) for ACK retries.",
    )
    ack_retry_max_ms: PositiveInt = Field(
        default=5000,
        description="Maximum backoff (milliseconds) for ACK retries.",
    )
    ack_retry_attempts: PositiveInt = Field(
        default=6,
        description="Maximum retry attempts when awaiting ACKs.",
    )
    session_accept_timeout_seconds: PositiveInt = Field(
        default=10,
        description="Seconds to wait for control.session.accept after handshake/register or resume.",
    )
    session_window_size: PositiveInt = Field(
        default=64,
        description="Sliding window size for session sequencing and ACK bitmaps.",
    )
    reconnect_base_delay_seconds: float = Field(
        default=1.0,
        description="Base delay for transport reconnection backoff.",
    )
    reconnect_max_delay_seconds: float = Field(
        default=30.0,
        description="Maximum delay for transport reconnection backoff.",
    )
    reconnect_jitter: float = Field(
        default=0.2,
        description="Jitter factor applied to reconnection backoff (0.0-1.0).",
    )

    concurrency_max_parallel: PositiveInt = Field(
        default=1,
        description="Maximum parallel tasks the worker is willing to accept.",
    )
    concurrency_per_node_limits: Dict[str, PositiveInt] | None = Field(
        default=None,
        description="Optional per-node concurrency limits enforced locally.",
    )
    runtime_names: list[str] = Field(
        default_factory=lambda: ["python"],
        description="Runtime identifiers supported by this worker.",
    )
    feature_flags: list[str] = Field(
        default_factory=list,
        description="Feature flags advertised to the scheduler.",
    )
    payload_types: list[str] = Field(
        default_factory=lambda: [
            "biz.exec.dispatch",
            "biz.exec.result",
            "biz.exec.feedback",
            "biz.exec.error",
            "biz.exec.next.request",
            "biz.exec.next.response",
            "biz.pkg.install",
            "biz.pkg.uninstall",
            "biz.pkg.event",
            "biz.pkg.catalog",
        ],
        description="Business/extension payload types this worker can handle.",
    )

    # Runtime layout
    packages_dir: Path = Field(
        default_factory=_default_packages_dir,
        description="Directory for installed node packages.",
    )
    data_dir: Path = Field(
        default=Path("./var/data"),
        description="Directory for ephemeral run data.",
    )
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Minimum log level for the worker process.",
    )

    @field_validator("log_level", mode="before")
    @classmethod
    def _normalize_log_level(cls, value: str) -> str:
        if isinstance(value, str):
            return value.upper()
        return value

    config_path: Path | None = Field(
        default=None,
        description="Resolved path to the on-disk config that seeded the settings.",
        exclude=True,
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[WorkerSettings],
        init_settings,
        env_settings,
        dotenv_settings,
        file_secret_settings,
    ):
        return (
            init_settings,
            cls._yaml_settings_source,
            env_settings,
            dotenv_settings,
            file_secret_settings,
        )

    @staticmethod
    def _yaml_settings_source(settings_cls: type[WorkerSettings] | None = None) -> Dict[str, Any]:
        candidates: Iterable[Path] = WorkerSettings._resolve_candidate_paths()

        for path in candidates:
            data = WorkerSettings._load_file(path)
            if data is not None:
                data.setdefault("config_path", path)
                return data
        return {}

    @staticmethod
    def _resolve_candidate_paths() -> Iterable[Path]:
        explicit = os.getenv("ASTRA_WORKER_CONFIG_FILE")
        if explicit:
            yield Path(explicit).expanduser()
        yield from DEFAULT_CONFIG_LOCATIONS

    @staticmethod
    def _load_file(path: Path) -> Dict[str, Any] | None:
        if not path.is_file():
            return None
        suffix = path.suffix.lower()
        try:
            with path.open("r", encoding="utf-8") as handle:
                if suffix in {".yaml", ".yml"}:
                    raw = yaml.safe_load(handle)
                elif suffix == ".json":
                    raw = json.load(handle)
                else:
                    return None
        except OSError as exc:
            raise RuntimeError(f"Failed to read worker config file {path}") from exc
        except (yaml.YAMLError, json.JSONDecodeError) as exc:
            raise ValueError(f"Invalid worker config file {path}") from exc

        if raw is None:
            return {}
        if not isinstance(raw, dict):
            raise ValueError(f"Worker config file {path} must contain a mapping at top level.")
        return raw


@lru_cache()
def get_settings() -> WorkerSettings:
    """Return memoized worker settings."""

    settings = WorkerSettings()
    # Ensure path fields are absolute for downstream use
    settings.packages_dir = settings.packages_dir.expanduser().resolve()
    settings.data_dir = settings.data_dir.expanduser().resolve()
    return settings
