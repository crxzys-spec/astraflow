#!/usr/bin/env python3
"""Simple helper to POST a workflow run against the local scheduler."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_PAYLOAD: Dict[str, Any] = {
    "clientId": "cli-demo",
    "workflow": {
        "id": "wf-demo",
        "schemaVersion": "2025-10",
        "metadata": {"name": "Demo Workflow"},
        "nodes": [
            {
                "id": "node-1",
                "type": "example.echo",
                "package": {"name": "example.pkg", "version": "1.0.0"},
                "label": "Echo Node",
                "position": {"x": 0, "y": 0},
                "parameters": {"message": "hello world"},
            }
        ],
        "edges": [],
    },
}


def load_payload(path: Path | None, message_override: str | None) -> Dict[str, Any]:
    if path and path.is_file():
        payload = json.loads(path.read_text(encoding="utf-8"))
    else:
        payload = json.loads(json.dumps(DEFAULT_PAYLOAD))
    if message_override is not None:
        try:
            payload["workflow"]["nodes"][0]["parameters"]["message"] = message_override
        except (KeyError, IndexError):
            pass
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--url",
        default="http://127.0.0.1:8080/api/v1/runs",
        help="Scheduler run submission endpoint (default: %(default)s)",
    )
    parser.add_argument(
        "--token",
        default=os.getenv("ASTRA_WORKER_AUTH_TOKEN", "dev-token"),
        help="Bearer token used for Authorization header (default: env ASTRA_WORKER_AUTH_TOKEN or 'dev-token')",
    )
    parser.add_argument(
        "--payload",
        type=Path,
        help="Optional path to a JSON file containing the run request payload.",
    )
    parser.add_argument(
        "--message",
        help="Override the 'message' parameter in the default workflow payload.",
    )
    args = parser.parse_args()

    payload = load_payload(args.payload, args.message)
    data = json.dumps(payload).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {args.token}",
    }
    request = Request(args.url, data=data, headers=headers, method="POST")
    try:
        with urlopen(request) as response:
            body = response.read().decode("utf-8")
            print(f"HTTP {response.status}")
            print(body)
            return 0
    except HTTPError as exc:
        print(f"HTTP {exc.code} {exc.reason}", file=sys.stderr)
        try:
            print(exc.read().decode("utf-8"), file=sys.stderr)
        except Exception:  # noqa: BLE001
            pass
        return 1
    except URLError as exc:
        print(f"Failed to reach scheduler: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
