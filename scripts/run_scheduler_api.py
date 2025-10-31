"""Helper to launch the scheduler API with the correct import paths."""

from __future__ import annotations

import sys
from pathlib import Path

import uvicorn


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    scheduler_src = repo_root / "scheduler" / "src"

    sys.path.insert(0, str(repo_root))
    sys.path.insert(0, str(scheduler_src))

    uvicorn.run(
        "scheduler_api.main:app",
        host="127.0.0.1",
        port=8080,
        reload=False,
    )


if __name__ == "__main__":
    main()
