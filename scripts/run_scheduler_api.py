"""Helper to launch the scheduler API with the correct import paths."""

from __future__ import annotations

import argparse
import errno
import os
import sys
from pathlib import Path
from typing import Final

import uvicorn
import socket


DEFAULT_HOST: Final[str] = "127.0.0.1"
DEFAULT_PORT: Final[int] = 8080
PORT_IN_USE_MESSAGE: Final[str] = (
    "Scheduler API failed to start: {host}:{port} is already in use.\n"
    "Stop the conflicting process or choose another port via --port or "
    "SCHEDULER_API_PORT."
)
WINDOWS_IN_USE_ERRORS: Final[set[int]] = {10013, 10048}


def _truthy_env(var_name: str, default: bool = False) -> bool:
    value = os.getenv(var_name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the scheduler API locally.")
    parser.add_argument("--host", default=os.getenv("SCHEDULER_API_HOST", DEFAULT_HOST))
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Port to bind to. Defaults to SCHEDULER_API_PORT or 8080.",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable uvicorn auto-reload (or set SCHEDULER_API_RELOAD=1).",
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

    host = args.host
    port_env = os.getenv("SCHEDULER_API_PORT")
    port = args.port or (int(port_env) if port_env else DEFAULT_PORT)
    reload = args.reload or _truthy_env("SCHEDULER_API_RELOAD")

    ensure_port_available(host, port)

    uvicorn.run(
        "scheduler_api.main:app",
        host=host,
        port=port,
        reload=reload,
    )


if __name__ == "__main__":
    main()
