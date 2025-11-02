"""Demo handlers used to showcase workflow builder capabilities."""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from typing import Any, Dict

from worker.agent.runner.context import ExecutionContext

LOGGER = logging.getLogger(__name__)


async def load_config(context: ExecutionContext) -> Dict[str, Any]:
  """Parse JSON configuration text."""
  raw_config = context.params.get("config", "{}")
  try:
    parsed = json.loads(raw_config)
  except json.JSONDecodeError as exc:
    message = f"Invalid JSON: {exc}"
    LOGGER.warning("load_config failed run=%s node=%s error=%s", context.run_id, context.node_id, message)
    return {
      "status": "failed",
      "error": message,
    }
  key_count = len(parsed) if isinstance(parsed, dict) else 0
  return {
    "status": "succeeded",
    "config": parsed,
    "keyCount": key_count,
  }


async def transform_text(context: ExecutionContext) -> Dict[str, Any]:
  """Apply simple text transformation."""
  text = context.params.get("text", "")
  mode = context.params.get("mode", "uppercase").lower()
  output = text
  if mode == "uppercase":
    output = text.upper()
  elif mode == "lowercase":
    output = text.lower()
  elif mode == "title":
    output = text.title()
  elif mode == "reverse":
    output = text[::-1]
  else:
    LOGGER.warning(
      "Unknown transform mode '%s' run=%s node=%s. Falling back to original text.",
      mode,
      context.run_id,
      context.node_id,
    )
  return {
    "status": "succeeded",
    "output": output,
    "modeApplied": mode,
  }


async def delay(context: ExecutionContext) -> Dict[str, Any]:
  """Sleep for the requested duration to simulate a slow task."""
  try:
    duration = float(context.params.get("durationSeconds", 0))
  except (TypeError, ValueError):
    duration = 0
  duration = max(duration, 0.0)
  start = time.perf_counter()
  await asyncio.sleep(duration)
  elapsed = time.perf_counter() - start
  return {
    "status": "succeeded",
    "durationSeconds": round(elapsed, 3),
  }


async def send_notification(context: ExecutionContext) -> Dict[str, Any]:
  """Simulate sending a notification by logging the payload."""
  recipient = context.params.get("recipient") or "unknown"
  channel = context.params.get("channel") or "email"
  message = context.params.get("message") or ""
  notification_id = str(uuid.uuid4())
  LOGGER.info(
    "Notification queued run=%s node=%s id=%s channel=%s recipient=%s message=%s",
    context.run_id,
    context.node_id,
    notification_id,
    channel,
    recipient,
    message,
  )
  return {
    "status": "succeeded",
    "notificationId": notification_id,
  }


async def audit_log(context: ExecutionContext) -> Dict[str, Any]:
  """Produce an audit entry describing the workflow event."""
  level = (context.params.get("level") or "info").upper()
  message = context.params.get("message") or "Workflow step completed."
  entry = {
    "level": level,
    "message": message,
    "runId": context.run_id,
    "nodeId": context.node_id,
    "package": f"{context.package_name}@{context.package_version}",
  }
  LOGGER.log(getattr(logging, level, logging.INFO), "Audit log entry: %s", entry)
  return {
    "status": "succeeded",
    "entry": entry,
  }

