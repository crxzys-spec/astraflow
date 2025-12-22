"""Run scheduler pytest suite with the correct import paths."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    scheduler_src = repo_root / "scheduler" / "src"

    pytest_args = sys.argv[1:] or ["scheduler/tests"]
    env = os.environ.copy()
    pythonpath = os.pathsep.join([str(repo_root), str(scheduler_src)])
    if env.get("PYTHONPATH"):
        pythonpath = os.pathsep.join([pythonpath, env["PYTHONPATH"]])
    env["PYTHONPATH"] = pythonpath

    result = subprocess.run(
        [sys.executable, "-m", "pytest", *pytest_args],
        cwd=str(repo_root),
        env=env,
    )
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
