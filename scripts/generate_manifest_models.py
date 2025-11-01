#!/usr/bin/env python3
"""Generate manifest models for Python (Pydantic) and TypeScript."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).absolute().parents[1]
SCHEMA_PATH = ROOT / "docs" / "schema" / "manifest.json"
PYTHON_OUTPUT = ROOT / "shared" / "models" / "manifest.py"
TYPESCRIPT_OUTPUT = ROOT / "dashboard" / "src" / "schema" / "manifest.ts"


def run(command: list[str], *, cwd: Path | None = None) -> None:
    """Run a subprocess command and forward output."""
    subprocess.run(command, check=True, cwd=cwd)


def generate_python_models() -> None:
    """Generate Pydantic models from the manifest schema."""
    PYTHON_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable,
        "-m",
        "datamodel_code_generator",
        "--input",
        str(SCHEMA_PATH),
        "--input-file-type",
        "jsonschema",
        "--output",
        str(PYTHON_OUTPUT),
        "--output-model-type",
        "pydantic_v2.BaseModel",
        "--target-python-version",
        "3.11",
        "--use-standard-collections",
        "--disable-timestamp",
    ]
    run(command)


def generate_typescript_models() -> None:
    """Generate TypeScript types from the manifest schema."""
    TYPESCRIPT_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    dashboard_dir = ROOT / "dashboard"
    schema_arg = Path("..") / "docs" / "schema" / "manifest.json"
    output_arg = Path("src") / "schema" / "manifest.ts"
    args = [
        "json-schema-to-typescript",
        "--input",
        str(schema_arg),
        "--output",
        str(output_arg),
        "--style.singleQuote",
    ]
    npx_executable = "npx.cmd" if os.name == "nt" else "npx"
    command = [npx_executable, *args]
    run(command, cwd=dashboard_dir)

    banner_line = "// Generated from docs/schema/manifest.json. Do not edit manually."
    content = TYPESCRIPT_OUTPUT.read_text(encoding="utf-8")
    if banner_line not in content:
        if content.startswith("/* eslint-disable */"):
            updated = content.replace(
                "/* eslint-disable */",
                "/* eslint-disable */\n" + banner_line,
                1,
            )
            TYPESCRIPT_OUTPUT.write_text(updated, encoding="utf-8")
        else:
            TYPESCRIPT_OUTPUT.write_text(
                "/* eslint-disable */\n" + banner_line + "\n\n" + content,
                encoding="utf-8",
            )


def main() -> None:
    if not SCHEMA_PATH.exists():
        raise SystemExit(f"Manifest schema not found: {SCHEMA_PATH}")
    generate_python_models()
    generate_typescript_models()


if __name__ == "__main__":
    main()
