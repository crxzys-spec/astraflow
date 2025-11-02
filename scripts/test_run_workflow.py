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
                "id": "node-config",
                "type": "example.pkg.load_config",
                "package": {"name": "example.pkg", "version": "1.0.0"},
                "status": "published",
                "category": "Examples",
                "label": "Load Configuration",
                "position": {"x": 0, "y": 0},
                "parameters": {
                    "config": "{\n  \"recipient\": \"demo@example.com\",\n  \"channel\": \"email\",\n  \"message\": \"Hello from AstraFlow!\"\n}"
                },
            },
            {
                "id": "node-transform",
                "type": "example.pkg.transform_text",
                "package": {"name": "example.pkg", "version": "1.0.0"},
                "status": "published",
                "category": "Examples",
                "label": "Transform Text",
                "position": {"x": 280, "y": 0},
                "parameters": {"text": "Hello from AstraFlow!", "mode": "uppercase"},
            },
            {
                "id": "node-delay",
                "type": "example.pkg.delay",
                "package": {"name": "example.pkg", "version": "1.0.0"},
                "status": "published",
                "category": "Examples",
                "label": "Delay",
                "position": {"x": 560, "y": 0},
                "parameters": {"durationSeconds": 1.5},
            },
            {
                "id": "node-notify",
                "type": "example.pkg.send_notification",
                "package": {"name": "example.pkg", "version": "1.0.0"},
                "status": "published",
                "category": "Examples",
                "label": "Send Notification",
                "position": {"x": 840, "y": 0},
                "parameters": {
                    "recipient": "demo@example.com",
                    "channel": "email",
                    "message": "Hello from AstraFlow!",
                },
            },
            {
                "id": "node-audit",
                "type": "example.pkg.audit_log",
                "package": {"name": "example.pkg", "version": "1.0.0"},
                "status": "published",
                "category": "Examples",
                "label": "Audit Log",
                "position": {"x": 1120, "y": 0},
                "parameters": {"level": "info", "message": "Demo workflow completed."},
            },
        ],
        "edges": [
            {"id": "edge-1", "source": {"node": "node-config", "port": "output"}, "target": {"node": "node-transform", "port": "input"}},
            {"id": "edge-2", "source": {"node": "node-transform", "port": "output"}, "target": {"node": "node-delay", "port": "input"}},
            {"id": "edge-3", "source": {"node": "node-delay", "port": "output"}, "target": {"node": "node-notify", "port": "input"}},
            {"id": "edge-4", "source": {"node": "node-notify", "port": "output"}, "target": {"node": "node-audit", "port": "input"}},
        ],
    },
}


def load_payload(path: Path | None, message_override: str | None) -> Dict[str, Any]:
    if path and path.is_file():
        payload = json.loads(path.read_text(encoding="utf-8"))
    else:
        payload = json.loads(json.dumps(DEFAULT_PAYLOAD))
    if message_override is not None:
        for node in payload["workflow"]["nodes"]:
            node_type = node.get("type")
            if node_type == "example.pkg.transform_text":
                node.setdefault("parameters", {})["text"] = message_override
            if node_type == "example.pkg.send_notification":
                node.setdefault("parameters", {})["message"] = message_override
    return payload
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
