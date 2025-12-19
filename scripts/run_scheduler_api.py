"""Helper to launch the scheduler API with the correct import paths."""

from __future__ import annotations

import argparse
import errno
import logging
import socket
import sys
from pathlib import Path
from typing import Final

import uvicorn

DEFAULT_HOST: Final[str] = "127.0.0.1"
DEFAULT_PORT: Final[int] = 8080
PORT_IN_USE_MESSAGE: Final[str] = (
    "Scheduler API failed to start: {host}:{port} is already in use.\n"
    "Stop the conflicting process or choose another port via --port or "
    "SCHEDULER_API_PORT."
)
WINDOWS_IN_USE_ERRORS: Final[set[int]] = {10013, 10048}
DEFAULT_LOG_LEVEL: Final[str] = "info"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the scheduler API locally.")
    parser.add_argument("--host", default=None, help="Bind address (overrides settings/env).")
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Port to bind to (overrides settings/env).",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable uvicorn auto-reload (overrides settings/env).",
    )
    parser.add_argument(
        "--log-level",
        choices=["critical", "error", "warning", "info", "debug", "trace"],
        default=None,
        help="Log level for scheduler and uvicorn output (overrides settings/env).",
    )
    return parser.parse_args()


def _port_in_use(exc: OSError) -> bool:
    if exc.errno == errno.EADDRINUSE:
        return True
    winerror = getattr(exc, "winerror", None)
    if isinstance(winerror, int) and winerror in WINDOWS_IN_USE_ERRORS:
        return True
    return False


def ensure_port_available(host: str, port: int) -> None:
    try:
        addr_info = socket.getaddrinfo(host, port, socket.AF_UNSPEC, socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise SystemExit(f"Unable to resolve host '{host}': {exc}") from exc

    last_error: OSError | None = None
    for family, socktype, proto, _, sockaddr in addr_info:
        try:
            with socket.socket(family, socktype, proto) as test_sock:
                test_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                test_sock.bind(sockaddr)
        except OSError as exc:
            last_error = exc
            if _port_in_use(exc):
                raise SystemExit(PORT_IN_USE_MESSAGE.format(host=host, port=port)) from exc
            continue
        else:
            return

    if last_error is not None:
        raise SystemExit(
            f"Unable to validate port availability for {host}:{port}: {last_error}"
        ) from last_error
    raise SystemExit(f"No suitable address family found for {host}:{port}.")


def main() -> None:
    args = parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    scheduler_src = repo_root / "scheduler" / "src"

    sys.path.insert(0, str(repo_root))
    sys.path.insert(0, str(scheduler_src))

    # Import after sys.path is adjusted
    from scheduler_api.config.settings import get_api_settings

    api_settings = get_api_settings()

    host = args.host or api_settings.host
    port = args.port or api_settings.port
    reload = args.reload or api_settings.reload
    log_level = (args.log_level or api_settings.log_level or DEFAULT_LOG_LEVEL).lower()
    if log_level == "trace":
        # Uvicorn treats "trace" as the most verbose level; map to DEBUG for stdlib logging.
        root_level = logging.DEBUG
    else:
        root_level = getattr(logging, log_level.upper(), logging.INFO)

    logging.basicConfig(level=root_level, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logging.getLogger(logger_name).setLevel(root_level)

    ensure_port_available(host, port)

    uvicorn.run(
        "scheduler_api.app:app",
        host=host,
        port=port,
        reload=reload,
        log_level=log_level if log_level != "trace" else "debug",
        log_config=None,
    )


if __name__ == "__main__":
    main()
