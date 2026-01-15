#!/usr/bin/env python3
"""Publish a local node package to Hub via the Scheduler API."""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Optional
from urllib import error, request


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", required=True, help="Local package name.")
    parser.add_argument(
        "--version",
        default=None,
        help="Optional package version (defaults to latest local version).",
    )
    parser.add_argument(
        "--visibility",
        choices=["private", "internal", "public"],
        default="private",
        help="Hub visibility for the package.",
    )
    parser.add_argument("--summary", default=None, help="Optional package summary.")
    parser.add_argument("--readme", default=None, help="Optional readme content.")
    parser.add_argument(
        "--readme-file",
        default=None,
        help="Optional path to a README file to publish.",
    )
    parser.add_argument(
        "--tags",
        default=None,
        help="Comma-separated list of tags.",
    )
    parser.add_argument(
        "--endpoint",
        default="http://localhost:9000/api/v1/hub/packages/local",
        help="Scheduler local package publish endpoint.",
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


def read_readme(readme: Optional[str], readme_file: Optional[str]) -> Optional[str]:
    if readme:
        return readme
    if not readme_file:
        return None
    try:
        return open(readme_file, "r", encoding="utf-8").read()
    except OSError as exc:
        sys.exit(f"Error: unable to read README file: {exc}")


def build_payload(args: argparse.Namespace) -> dict:
    payload: dict[str, object] = {"name": args.name}
    if args.version:
        payload["version"] = args.version
    if args.visibility:
        payload["visibility"] = args.visibility
    if args.summary:
        payload["summary"] = args.summary
    readme = read_readme(args.readme, args.readme_file)
    if readme:
        payload["readme"] = readme
    if args.tags:
        tags = [tag.strip() for tag in args.tags.split(",") if tag.strip()]
        if tags:
            payload["tags"] = tags
    return payload


def publish_package(endpoint: str, token: str, payload: dict) -> None:
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
            print(f"Package published (HTTP {resp.status}). Response:\n{body}")
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
    publish_package(args.endpoint, token, payload)


if __name__ == "__main__":
    main()
