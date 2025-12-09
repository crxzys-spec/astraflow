#!/usr/bin/env python
"""Synchronise packages into the shared node-packages repository.

Usage:
    python scripts/install_package.py node-packages/example_pkg/1.0.0 [...]

By default the script assumes it is executed from the repository root and that
source packages live under ``node-packages`` while installed packages should be
placed under ``node-packages``. You can override those roots with the optional
flags if needed.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "packages",
        nargs="+",
        help="Path(s) to package directories under node-packages (e.g. node-packages/example_pkg/1.0.0).",
    )
    parser.add_argument(
        "--source-root",
        default="node-packages",
        help="Root directory that contains source packages (default: node-packages).",
    )
    parser.add_argument(
        "--dest-root",
        default=os.getenv("ASTRA_PACKAGES_ROOT", "node-packages"),
        help="Root directory where node packages live (default: node-packages or ASTRA_PACKAGES_ROOT).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only print the actions that would be taken.",
    )
    return parser.parse_args()


def resolve_repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def normalise_path(path_str: str, base: Path) -> Path:
    candidate = Path(path_str)
    if not candidate.is_absolute():
        candidate = base / candidate
    return candidate.resolve()


def copy_package(src: Path, dest: Path, dry_run: bool) -> None:
    print(f"Installing {src} -> {dest}")
    if dry_run:
        return
    if not src.is_dir():
        raise FileNotFoundError(f"Source package directory not found: {src}")
    if dest.exists():
        shutil.rmtree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src, dest)


def main() -> int:
    args = parse_args()
    repo_root = resolve_repo_root()
    source_root = normalise_path(args.source_root, repo_root)
    dest_root = normalise_path(args.dest_root, repo_root)

    for package_arg in args.packages:
        src = normalise_path(package_arg, repo_root)
        try:
            relative = src.relative_to(source_root)
        except ValueError as exc:
            raise ValueError(f"Package path {src} is not inside source root {source_root}") from exc
        dest = dest_root / relative
        copy_package(src, dest, args.dry_run)

    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
