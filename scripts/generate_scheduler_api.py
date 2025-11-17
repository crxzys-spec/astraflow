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
    ensure_custom_main(api_src / "main.py")


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


def ensure_custom_main(main_path: Path) -> None:
    """
    Overwrite the generated main module with our customised bootstrap.

    We layer CORS, control-plane routes, and startup hooks that upgrade the
    database, reload the package catalog, and seed demo data. OpenAPI generator
    will reset this file on each run, so we regenerate it here.
    """

    custom_main = '''# coding: utf-8

"""
    Scheduler Public API (v1)

    No description provided (generated by Openapi Generator https://github.com/openapitools/openapi-generator)

    The version of the OpenAPI document: 1.3.0
    Generated by OpenAPI Generator (https://openapi-generator.tech)

    Do not edit the class manually.
"""  # noqa: E501


from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from scheduler_api.apis.auth_api import router as AuthApiRouter
from scheduler_api.apis.events_api import router as EventsApiRouter
from scheduler_api.apis.packages_api import router as PackagesApiRouter
from scheduler_api.apis.runs_api import router as RunsApiRouter
from scheduler_api.apis.workers_api import router as WorkersApiRouter
from scheduler_api.apis.workflows_api import router as WorkflowsApiRouter
from scheduler_api.catalog import catalog
from scheduler_api.control_plane import router as ControlPlaneRouter
from scheduler_api.db.migrations import upgrade_database
from scheduler_api.db.seed_data import seed_demo_workflow

app = FastAPI(
    title="Scheduler Public API (v1)",
    description="No description provided (generated by Openapi Generator https://github.com/openapitools/openapi-generator)",
    version="1.3.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://10.0.35.8:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(AuthApiRouter)
app.include_router(EventsApiRouter)
app.include_router(PackagesApiRouter)
app.include_router(RunsApiRouter)
app.include_router(WorkersApiRouter)
app.include_router(WorkflowsApiRouter)
app.include_router(ControlPlaneRouter)


@app.on_event("startup")
def _startup() -> None:
    upgrade_database()
    catalog.reload()
    seed_demo_workflow()
'''
    main_path.write_text(custom_main, encoding="utf-8")


if __name__ == "__main__":
    main()
