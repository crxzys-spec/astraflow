#!/usr/bin/env python3
"""Generate Pydantic models from WebSocket JSON Schemas."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "docs" / "schema" / "ws"
OUTPUT_DIR = ROOT / "shared" / "models" / "ws"


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for schema_path in sorted(SCHEMA_DIR.glob("*.schema.json")):
        qualified_name = schema_path.stem.replace(".schema", "")
        parts = qualified_name.split(".")

        if len(parts) == 1:
            package_dir = OUTPUT_DIR
            module_name = parts[0]
        else:
            package_parts = [part for part in parts[:-1] if part]
            module_name = parts[-1]
            package_dir = OUTPUT_DIR.joinpath(*package_parts)
            package_dir.mkdir(parents=True, exist_ok=True)

            # Ensure every package directory has an __init__.py so relative imports work.
            current = package_dir
            while True:
                init_file = current / "__init__.py"
                if not init_file.exists():
                    init_file.write_text('"""Generated package."""\n', encoding="utf-8")
                if current == OUTPUT_DIR:
                    break
                current = current.parent
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        output_path = package_dir / f"{module_name}.py"
        cmd = [
            sys.executable,
            "-m",
            "datamodel_code_generator",
            "--input",
            str(schema_path),
            "--input-file-type",
            "jsonschema",
            "--output",
            str(output_path),
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--target-python-version",
            "3.11",
            "--disable-timestamp",
        ]
        subprocess.run(cmd, check=True)
    init_file = OUTPUT_DIR / "__init__.py"
    if not init_file.exists():
        init_file.write_text("# Generated models package\n", encoding="utf-8")


if __name__ == "__main__":
    main()
