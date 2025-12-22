#!/usr/bin/env python3
"""Generate FastAPI server stubs from OpenAPI spec."""

from __future__ import annotations

import os
import re
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
            "openapi-generator-cli.cmd",
            "openapi-generator-cli",
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
        spec_dir.mkdir(parents=True, exist_ok=True)

        spec = build_resolved_spec(OPENAPI_SPEC)
        spec_path = spec_dir / "openapi.yaml"
        spec_yaml = yaml.safe_dump(spec, sort_keys=False)
        spec_path.write_text(spec_yaml, encoding="utf-8")

        resolved_copy = OUTPUT_DIR / "openapi.resolved.yaml"
        resolved_copy.write_text(spec_yaml, encoding="utf-8")

        base_cmd = [
            "generate",
            "-i",
            "openapi.yaml",
            "-g",
            "python-fastapi",
            "-o",
            str(OUTPUT_DIR),
            "--additional-properties",
            "packageName=scheduler_api",
            # "--skip-validate-spec",
        ]
        if cli.lower().endswith(".ps1"):
            exec_cmd = [
                "powershell.exe",
                "-NoLogo",
                "-NoProfile",
                "-File",
                cli,
                *base_cmd,
            ]
        else:
            exec_cmd = [cli, *base_cmd]
        subprocess.run(exec_cmd, check=True, cwd=str(spec_dir))

    api_src = OUTPUT_DIR / "src" / "scheduler_api"
    postprocess_generated_models(api_src / "models")
    relax_field_strictness(api_src / "apis")
    # Preserve the clean, resolved spec as the checked-in OpenAPI document
    (OUTPUT_DIR / "openapi.yaml").write_text(spec_yaml, encoding="utf-8")


def build_resolved_spec(openapi_path: Path) -> dict:
    """Load docs OpenAPI and inline all refs/components for generator stability."""

    src_root = openapi_path.parent
    spec = yaml.safe_load(openapi_path.read_text(encoding="utf-8"))
    components = spec.setdefault("components", {})

    merge_sources = {
        "parameters": src_root / "components" / "parameters.yaml",
        "responses": src_root / "components" / "responses.yaml",
        "schemas": src_root / "components" / "schemas" / "index.yaml",
    }
    for key, path in merge_sources.items():
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and key in data:
            components[key] = data[key]
        else:
            components[key] = data if isinstance(data, dict) else {}

    paths = spec.get("paths", {})
    for route, body in list(paths.items()):
        if isinstance(body, dict) and "$ref" in body:
            ref_path = (src_root / Path(body["$ref"])).resolve()
            paths[route] = yaml.safe_load(ref_path.read_text(encoding="utf-8"))

    def transform_refs(node):
        if isinstance(node, dict):
            return {k: transform_refs(v) for k, v in node.items()}
        if isinstance(node, list):
            return [transform_refs(v) for v in node]
        if isinstance(node, str):
            replacements = {
                "../components/parameters.yaml#/parameters/": "#/components/parameters/",
                "../components/parameters.yaml#/": "#/components/parameters/",
                "../components/responses.yaml#/responses/": "#/components/responses/",
                "../components/responses.yaml#/": "#/components/responses/",
                "../components/schemas/index.yaml#/schemas/": "#/components/schemas/",
                "../components/schemas/index.yaml#/": "#/components/schemas/",
                "./components/schemas/index.yaml#/schemas/": "#/components/schemas/",
                "./schemas/index.yaml#/schemas/": "#/components/schemas/",
                "./schemas/index.yaml#/": "#/components/schemas/",
            }
            for old, new in replacements.items():
                node = node.replace(old, new)
            if node.startswith("#/") and not node.startswith("#/components/"):
                node = node.replace("#/", "#/components/schemas/", 1)
            if node.startswith("#/schemas/"):
                node = node.replace("#/schemas/", "#/components/schemas/")
            if node.startswith("#/parameters/"):
                node = node.replace("#/parameters/", "#/components/parameters/")
            if node.startswith("#/responses/"):
                node = node.replace("#/responses/", "#/components/responses/")
            return node
        return node

    spec = transform_refs(spec)

    def strip_const(node):
        if isinstance(node, dict):
            node.pop("const", None)
            for k, v in list(node.items()):
                node[k] = strip_const(v)
        elif isinstance(node, list):
            return [strip_const(v) for v in node]
        return node

    spec = strip_const(spec)
    spec["openapi"] = "3.0.3"
    return spec


def postprocess_generated_models(models_root: Path) -> None:
    """
    Apply fixups to openapi-generator output so repeated regeneration is stable.

    python-fastapi currently emits ``one_of_schemas: List[str] = Literal[...]`` which
    Pydantic v2 cannot serialise (it produces a ``typing._LiteralGenericAlias`` at runtime).
    We rewrite that declaration to ``ClassVar[List[str]]`` and adjust imports accordingly.
    """

    literal_pattern = re.compile(
        r"(one_of_schemas:\s*)List\[str\]\s*=\s*Literal\[(?P<values>[^\]]+)\]"
    )

    for path in models_root.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if "one_of_schemas" not in text:
            continue

        def _replace(match: re.Match[str]) -> str:
            values = match.group("values")
            return f"{match.group(1)}ClassVar[List[str]] = [{values}]"

        new_text, count = literal_pattern.subn(_replace, text)
        if not count:
            continue

        if "ClassVar" not in new_text:
            new_text = re.sub(
                r"from typing import ([^\n]+)",
                lambda m: _inject_classvar_import(m.group(0), m.group(1)),
                new_text,
                count=1,
            )

        if "Literal" not in new_text:
            new_text = re.sub(
                r"from typing_extensions import Literal[^\n]*\n",
                "",
                new_text,
            )

        path.write_text(new_text, encoding="utf-8")


def _inject_classvar_import(statement: str, imports: str) -> str:
    items = [item.strip() for item in imports.split(",")]
    if "ClassVar" not in items:
        items.append("ClassVar")
    ordered: list[str] = []
    seen: set[str] = set()
    for item in items:
        if item and item not in seen:
            ordered.append(item)
            seen.add(item)
    return f"from typing import {', '.join(ordered)}"


def relax_field_strictness(apis_root: Path) -> None:
    """
    OpenAPI generator emits Field(..., strict=True, ...) for numeric query params which FastAPI
    then refuses to coerce from strings (all query params arrive as strings). Remove those flags
    so the default conversion logic applies.
    """

    for path in apis_root.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if "strict=True" not in text:
            continue
        new_text = re.sub(r"strict=True,\s*", "", text)
        new_text = re.sub(r",\s*strict=True", "", new_text)
        if new_text != text:
            path.write_text(new_text, encoding="utf-8")


if __name__ == "__main__":
    main()
