#!/usr/bin/env python3
"""Generate FastAPI server stubs from OpenAPI spec."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
OPENAPI_SPEC = ROOT / "docs" / "api" / "v1" / "openapi.yaml"
OUTPUT_DIR = ROOT / "scheduler"


def resolve_cli() -> str:
    """Locate the openapi-generator executable."""

    env_cli = os.environ.get("OPENAPI_GENERATOR_CLI")
    candidates: list[str] = []
    if env_cli:
        candidates.append(env_cli)
    candidates.extend(
        [
            "openapi-generator-cli",
            "openapi-generator-cli.cmd",
        ]
    )

    for candidate in candidates:
        if os.path.sep in candidate:
            path = Path(candidate)
            if path.exists():
                return str(path)
        else:
            located = shutil.which(candidate)
            if located:
                return located

    raise FileNotFoundError(
        "Unable to locate openapi-generator-cli. "
        "Install it globally or set OPENAPI_GENERATOR_CLI to the executable path."
    )


def main() -> None:
    cli = resolve_cli()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmpdir:
        spec_dir = Path(tmpdir) / "api"
        shutil.copytree(OPENAPI_SPEC.parent, spec_dir, dirs_exist_ok=True)
        spec_path = spec_dir / "openapi.yaml"
        spec = yaml.safe_load(spec_path.read_text(encoding="utf-8"))

        components = spec.setdefault("components", {})
        merge_sources = {
            "parameters": spec_dir / "components" / "parameters.yaml",
            "responses": spec_dir / "components" / "responses.yaml",
            "schemas": spec_dir / "components" / "schemas" / "index.yaml",
        }
        for key, path in merge_sources.items():
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
            # each file wraps content under the same key (e.g. {'parameters': {...}})
            components[key] = data.get(key, {})

        def transform_refs(node):
            if isinstance(node, dict):
                return {k: transform_refs(v) for k, v in node.items()}
            if isinstance(node, list):
                return [transform_refs(v) for v in node]
            if isinstance(node, str):
                replacements = {
                    "../components/parameters.yaml#/parameters/": "#/components/parameters/",
                    "../components/responses.yaml#/responses/": "#/components/responses/",
                    "../components/schemas/index.yaml#/schemas/": "#/components/schemas/",
                    "./components/schemas/index.yaml#/schemas/": "#/components/schemas/",
                    "./schemas/index.yaml#/schemas/": "#/components/schemas/",
                }
                for old, new in replacements.items():
                    node = node.replace(old, new)
                if node.startswith("#/schemas/"):
                    node = node.replace("#/schemas/", "#/components/schemas/")
                if node.startswith("#/parameters/"):
                    node = node.replace("#/parameters/", "#/components/parameters/")
                if node.startswith("#/responses/"):
                    node = node.replace("#/responses/", "#/components/responses/")
                return node
            return node

        spec = transform_refs(spec)

        spec_path.write_text(yaml.safe_dump(spec, sort_keys=False), encoding="utf-8")

        cmd = [
            cli,
            "generate",
            "-i",
            "openapi.yaml",
            "-g",
            "python-fastapi",
            "-o",
            str(OUTPUT_DIR),
            "--additional-properties",
            "packageName=scheduler_api",
        ]
        subprocess.run(cmd, check=True, cwd=str(spec_dir))


if __name__ == "__main__":
    main()
