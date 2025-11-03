"""Demo handlers used to showcase workflow builder capabilities."""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from typing import Any, Dict

from worker.agent.runner.context import ExecutionContext
from shared.models.ws.feedback import FeedbackChannel

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



async def feedback_showcase(context: ExecutionContext) -> Dict[str, Any]:
  """Demonstrate streaming feedback, progress, metrics, and binary chunks."""
  prompt = context.params.get("prompt") or "Hello from AstraFlow!"
  delay_ms = context.params.get("tokenDelayMs", 80)
  try:
    delay = max(0.0, float(delay_ms) / 1000.0)
  except (TypeError, ValueError):
    delay = 0.08
  reporter = context.feedback
  tokens = list(prompt)
  total = len(tokens) or 1
  assembled: list[str] = []
  counter_width = len(str(total))
  if reporter:
    await reporter.send(
      stage="initialising",
      progress=0.02,
      message=f"Streaming tokens {0:0{counter_width}d}/{total:0{counter_width}d} (000.0%)",
      metrics={"tokens_total": total},
    )
  for index, token in enumerate(tokens):
    assembled.append(token)
    await asyncio.sleep(delay)
    if reporter:
      streamed = index + 1
      fraction = streamed / total
      progress = round(0.05 + 0.8 * fraction, 4)
      percent = round(fraction * 100, 1)
      await reporter.send(
        stage="streaming",
        progress=progress,
        message=f"Streaming tokens {streamed:0{counter_width}d}/{total:0{counter_width}d} ({percent:05.1f}%)",
        chunks=[{"channel": FeedbackChannel.llm.value, "text": token}],
        metrics={"tokens_streamed": streamed, "percent_complete": percent},
      )
  summary = "".join(assembled)
  if reporter:
    await reporter.send(
      stage="streaming",
      message="Preview image ready",
      chunks=[{
        "channel": FeedbackChannel.custom.value,
        "mime_type": "image/png",
        "data_base64": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgYAAAAAMAAWgmWQ0AAAAASUVORK5CYII=",
        "metadata": {"description": "1x1 AstraFlow pixel"}
      }],
    )
    await reporter.send(
      stage="finalising",
      progress=0.98,
      message=f"Summarising feedback tokens ({total:0{counter_width}d}/{total:0{counter_width}d})",
      chunks=[{"channel": FeedbackChannel.log.value, "text": f"Generated {total} tokens"}],
      metrics={"tokens_total": total},
    )
    await reporter.send(
      stage="succeeded",
      progress=1.0,
      message=f"Feedback demo complete ({total:0{counter_width}d}/{total:0{counter_width}d})",
    )
  return {"status": "succeeded", "summary": summary, "tokenCount": len(summary)}
