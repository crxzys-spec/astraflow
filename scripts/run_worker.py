"""Bootstraps the worker control-plane loop with repository-relative imports."""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root))

    # Lazy import after adjusting sys.path
    from worker.config import get_settings  # type: ignore
    from worker.control_plane.runtime import run_forever  # type: ignore

    settings = get_settings()
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    asyncio.run(run_forever())


if __name__ == "__main__":
    main()
