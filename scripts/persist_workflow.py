#!/usr/bin/env python3
"""CLI helper to persist a workflow definition via the Scheduler API."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional
from urllib import error, request


def resolve_default_definition() -> Path:
    root = Path(__file__).resolve().parents[1]
    return root / "docs" / "examples" / "debug-workflow.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Persist a workflow definition using the Scheduler API.",
    )
    parser.add_argument(
        "--file",
        type=Path,
        default=resolve_default_definition(),
        help="Path to the workflow JSON definition (default: docs/examples/debug-workflow.json).",
    )
    parser.add_argument(
        "--endpoint",
        default="http://localhost:9000/api/v1/workflows",
        help="Scheduler workflow persistence endpoint.",
    )
    parser.add_argument(
        "--token",
        default=None,
        help="Bearer token for authentication (falls back to SCHEDULER_TOKEN env var).",
    )
    return parser.parse_args()


def load_token(explicit: Optional[str]) -> str:
    token = explicit or os.environ.get("SCHEDULER_TOKEN")
    if not token:
        sys.exit("Error: provide --token or set SCHEDULER_TOKEN in the environment.")
    return token


def persist_workflow(definition_path: Path, endpoint: str, token: str) -> None:
    if not definition_path.exists():
        sys.exit(f"Error: workflow definition not found: {definition_path}")

    payload = definition_path.read_text(encoding="utf-8")
    try:
        json.loads(payload)
    except json.JSONDecodeError as exc:
        sys.exit(f"Error: workflow JSON is invalid: {exc}")

    req = request.Request(
        endpoint,
        data=payload.encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
        method="POST",
    )

    try:
        with request.urlopen(req) as resp:
            body = resp.read().decode("utf-8")
            print(f"Workflow persisted (HTTP {resp.status}). Response:\n{body}")
    except error.HTTPError as http_err:
        detail = http_err.read().decode("utf-8", errors="ignore")
        sys.exit(
            f"Request failed (HTTP {http_err.code}). Endpoint: {endpoint}\nResponse: {detail}"
        )
    except error.URLError as url_err:
        sys.exit(f"Failed to reach {endpoint}: {url_err.reason}")


def main() -> None:
    args = parse_args()
    token = load_token(args.token)
    persist_workflow(args.file, args.endpoint, token)


if __name__ == "__main__":
    main()
