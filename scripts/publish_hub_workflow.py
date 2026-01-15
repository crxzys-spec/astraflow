#!/usr/bin/env python3
"""Publish a local workflow to Hub via the Scheduler API."""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Optional
from urllib import error, request


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workflow-id", required=True, help="Local workflow id.")
    parser.add_argument("--version", required=True, help="Workflow version to publish.")
    parser.add_argument("--name", default=None, help="Optional workflow name override.")
    parser.add_argument("--summary", default=None, help="Optional workflow summary.")
    parser.add_argument("--description", default=None, help="Optional workflow description.")
    parser.add_argument(
        "--visibility",
        choices=["private", "internal", "public"],
        default="private",
        help="Hub visibility for the workflow.",
    )
    parser.add_argument("--tags", default=None, help="Comma-separated list of tags.")
    parser.add_argument(
        "--endpoint",
        default="http://localhost:9000/api/v1/hub/workflows/local",
        help="Scheduler local workflow publish endpoint.",
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


def build_payload(args: argparse.Namespace) -> dict:
    payload: dict[str, object] = {
        "workflowId": args.workflow_id,
        "version": args.version,
        "visibility": args.visibility,
    }
    if args.name:
        payload["name"] = args.name
    if args.summary:
        payload["summary"] = args.summary
    if args.description:
        payload["description"] = args.description
    if args.tags:
        tags = [tag.strip() for tag in args.tags.split(",") if tag.strip()]
        if tags:
            payload["tags"] = tags
    return payload


def publish_workflow(endpoint: str, token: str, payload: dict) -> None:
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(
        endpoint,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
        method="POST",
    )
    try:
        with request.urlopen(req) as resp:
            body = resp.read().decode("utf-8")
            print(f"Workflow published (HTTP {resp.status}). Response:\n{body}")
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
    payload = build_payload(args)
    publish_workflow(args.endpoint, token, payload)


if __name__ == "__main__":
    main()
