"""Demo handlers used to showcase workflow builder capabilities."""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict

from worker.agent.runner.context import ExecutionContext
from shared.models.ws.feedback import FeedbackChannel

LOGGER = logging.getLogger(__name__)


class _AttrDict(dict):
  """Dictionary wrapper that exposes keys as attributes for templates."""

  def __getattr__(self, item: str) -> Any:
    value = self.get(item)
    if isinstance(value, dict) and not isinstance(value, _AttrDict):
      value = _AttrDict(value)
      dict.__setitem__(self, item, value)
    elif isinstance(value, list):
      converted = [_attrify(elem) for elem in value]
      dict.__setitem__(self, item, converted)
      value = converted
    return value


def _attrify(value: Any) -> Any:
  if isinstance(value, dict) and not isinstance(value, _AttrDict):
    return _AttrDict({key: _attrify(val) for key, val in value.items()})
  if isinstance(value, list):
    return [_attrify(item) for item in value]
  return value


def _parse_timestamp_ms(value: Any) -> float | None:
  """Best-effort conversion to milliseconds since epoch."""
  if value is None:
    return None
  if isinstance(value, (int, float)):
    return float(value)
  if isinstance(value, str):
    text = value.strip()
    if not text:
      return None
    if text.isdigit():
      try:
        return float(text)
      except ValueError:
        return None
    normalised = text.replace("Z", "+00:00")
    try:
      parsed = datetime.fromisoformat(normalised)
    except ValueError:
      return None
    return parsed.timestamp() * 1000.0
  return None


async def load_config(context: ExecutionContext) -> Dict[str, Any]:
  """Parse JSON configuration text."""
  raw_config = context.params.get("config", "{}")
  started_at = datetime.now(timezone.utc)
  started_at_ms = int(started_at.timestamp() * 1000)
  if isinstance(raw_config, dict):
    parsed = raw_config.copy()
  elif isinstance(raw_config, list):
    parsed = list(raw_config)
  else:
    if isinstance(raw_config, (bytes, bytearray)):
      try:
        raw_config = raw_config.decode("utf-8")
      except UnicodeDecodeError as exc:
        message = f"Invalid encoding: {exc}"
        LOGGER.warning("load_config failed run=%s node=%s error=%s", context.run_id, context.node_id, message)
        return {
          "status": "failed",
          "error": message,
        }
    if not isinstance(raw_config, str):
      raw_config = json.dumps(raw_config)
    try:
      parsed = json.loads(raw_config)
    except json.JSONDecodeError as exc:
      message = f"Invalid JSON: {exc}"
      LOGGER.warning("load_config failed run=%s node=%s error=%s", context.run_id, context.node_id, message)
      return {
        "status": "failed",
        "error": message,
      }
  if isinstance(parsed, dict):
    recipient = parsed.get("recipient") or {}
    if isinstance(recipient, str):
      recipient_record = {"email": recipient}
    elif isinstance(recipient, dict):
      recipient_record = recipient.copy()
    else:
      recipient_record = {}
    parsed["recipient"] = recipient_record
    name = recipient_record.get("name") or recipient_record.get("email") or "there"
    template = parsed.get("template") or parsed.get("message") or "Hello {{name}}, welcome to AstraFlow!"
    if not isinstance(template, str):
      template = json.dumps(template)
    subject = parsed.get("subject") or "Welcome to AstraFlow"
    parsed["subject"] = subject
    parsed.setdefault("channel", "email")
    parsed["message"] = template.replace("{{name}}", name)
    try:
      parsed["delaySeconds"] = float(parsed.get("delaySeconds", 1.5))
    except (TypeError, ValueError):
      parsed["delaySeconds"] = 1.5
    try:
      parsed["tokenDelayMs"] = max(0, int(parsed.get("tokenDelayMs", 80)))
    except (TypeError, ValueError):
      parsed["tokenDelayMs"] = 80
    parsed.setdefault("mode", "title")
  key_count = len(parsed) if isinstance(parsed, dict) else 0
  return {
    "status": "succeeded",
    "config": parsed,
    "keyCount": key_count,
    "startedAt": started_at.isoformat(),
    "startedAtMs": started_at_ms,
  }


async def transform_text(context: ExecutionContext) -> Dict[str, Any]:
  """Apply simple text transformation."""
  text_param = context.params.get("text", "")
  if isinstance(text_param, (dict, list)):
    text = json.dumps(text_param)
  else:
    text = str(text_param)
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
  recipient_param = context.params.get("recipient") or {}
  if isinstance(recipient_param, dict):
    recipient = recipient_param
  else:
    recipient = {"name": str(recipient_param)}
  channel = context.params.get("channel") or "email"
  subject = context.params.get("subject") or "Welcome"
  delay_seconds = context.params.get("delaySeconds")
  try:
    delay_seconds_value = float(delay_seconds) if delay_seconds is not None else None
  except (TypeError, ValueError):
    delay_seconds_value = None
  token_delay_ms = context.params.get("tokenDelayMs")
  try:
    token_delay_value = int(token_delay_ms) if token_delay_ms is not None else None
  except (TypeError, ValueError):
    token_delay_value = None
  summary = output
  return {
    "status": "succeeded",
    "output": output,
    "modeApplied": mode,
    "message": summary,
    "recipient": recipient,
    "channel": channel,
    "subject": subject,
    "delaySeconds": delay_seconds_value,
    "tokenDelayMs": token_delay_value,
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
  recipient_param = context.params.get("recipient") or {}
  if isinstance(recipient_param, dict):
    recipient = recipient_param.get("email") or recipient_param.get("name") or repr(recipient_param)
  else:
    recipient = str(recipient_param or "unknown")
  channel = context.params.get("channel") or "email"
  subject = context.params.get("subject") or "Notification"
  message = context.params.get("message") or ""
  notification_id = str(uuid.uuid4())
  LOGGER.info(
    "Notification queued run=%s node=%s id=%s channel=%s recipient=%s subject=%s message=%s",
    context.run_id,
    context.node_id,
    notification_id,
    channel,
    recipient,
    subject,
    message,
  )
  summary = f"Sent '{subject}' to {recipient} via {channel}. Notification ID {notification_id}."
  return {
    "status": "succeeded",
    "notificationId": notification_id,
    "summary": summary,
    "recipient": recipient_param,
    "channel": channel,
    "subject": subject,
    "message": message,
  }


async def audit_log(context: ExecutionContext) -> Dict[str, Any]:
  """Produce an audit entry describing the workflow event."""
  level = (context.params.get("level") or "info").upper()
  message = context.params.get("message") or "Workflow step completed."
  summary = context.params.get("summary") or message
  notification_id = context.params.get("notificationId")
  run_started_ms = (
    _parse_timestamp_ms(context.params.get("runStartedAtMs"))
    or _parse_timestamp_ms(context.params.get("startedAtMs"))
    or _parse_timestamp_ms(context.params.get("runStartedAt"))
  )
  now_ms = time.time() * 1000.0
  latency_ms = None
  if run_started_ms is not None:
    latency_ms = max(0.0, round(now_ms - run_started_ms, 3))
  if latency_ms is None:
    latency_ms = 0.0
  entry = {
    "level": level,
    "message": summary,
    "runId": context.run_id,
    "nodeId": context.node_id,
    "package": f"{context.package_name}@{context.package_version}",
  }
  if notification_id:
    entry["notificationId"] = notification_id
  entry["details"] = {
    key: value
    for key, value in context.params.items()
    if key not in {"level"}
  }
  if latency_ms is not None:
    entry["latencyMs"] = latency_ms
  LOGGER.log(getattr(logging, level, logging.INFO), "Audit log entry: %s", entry)
  return {
    "status": "succeeded",
    "latencyMs": latency_ms,
    "entry": entry,
  }


async def collect_metrics(context: ExecutionContext) -> Dict[str, Any]:
  """Record a synthetic metric for debugging."""
  metric_name = str(context.params.get("metricName") or "debug.metric")
  raw_value = context.params.get("value", 0)
  try:
    value = float(raw_value)
  except (TypeError, ValueError):
    LOGGER.warning(
      "Metric value invalid run=%s node=%s value=%r", context.run_id, context.node_id, raw_value
    )
    return {"status": "failed", "message": "Metric value must be numeric."}
  tags_param = context.params.get("tags") or {}
  tags = tags_param if isinstance(tags_param, dict) else {}
  metric_id = f"{metric_name}-{uuid.uuid4().hex[:8]}"
  LOGGER.info(
    "Metric reported run=%s node=%s metric=%s value=%s tags=%s metric_id=%s",
    context.run_id,
    context.node_id,
    metric_name,
    value,
    tags,
    metric_id,
  )
  return {
    "status": "succeeded",
    "metricId": metric_id,
    "metric": {
      "name": metric_name,
      "value": value,
      "tags": tags,
    },
  }


async def debug_gate(context: ExecutionContext) -> Dict[str, Any]:
  """Evaluate a boolean expression to gate downstream execution."""
  condition = str(context.params.get("condition") or "True")
  payload_raw = context.params.get("payload") or {}
  payload = _attrify(payload_raw) if isinstance(payload_raw, (dict, list)) else payload_raw
  env = {"payload": payload, "payload_raw": payload_raw}
  allowed = False
  error_message = None
  try:
    allowed = bool(eval(condition, {"__builtins__": {}}, env))  # noqa: S307
  except Exception as exc:  # noqa: BLE001
    error_message = f"Condition error: {exc}"
    LOGGER.warning(
      "debug_gate evaluation failed run=%s node=%s error=%s condition=%s payload=%s",
      context.run_id,
      context.node_id,
      exc,
      condition,
      payload_raw,
    )
  status = "allowed" if allowed else "blocked"
  message = error_message or f"Condition '{condition}' evaluated to {allowed}"
  LOGGER.info(
    "debug_gate decision run=%s node=%s status=%s condition=%s payload=%s",
    context.run_id,
    context.node_id,
    status,
    condition,
    payload_raw,
  )
  return {
    "status": status,
    "allow": allowed,
    "message": message,
    "payload": payload_raw,
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
  last_summary_sent = ""
  summary_emit_interval = max(1, total // 4)
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
      summary_text = "".join(assembled)
      await reporter.send(
        stage="streaming",
        progress=progress,
        message=f"Streaming tokens {streamed:0{counter_width}d}/{total:0{counter_width}d} ({percent:05.1f}%)",
        chunks=[{"channel": FeedbackChannel.llm.value, "text": token}],
        metrics={"tokens_streamed": streamed, "percent_complete": percent},
        metadata={"results": {"summary": summary_text}} if summary_text else None,
      )
      if (
        reporter
        and summary_text
        and (streamed % summary_emit_interval == 0 or streamed == total)
        and summary_text != last_summary_sent
      ):
        last_summary_sent = summary_text
        await reporter.send(
          stage="streaming",
          metadata={
            "results": {"summary": summary_text},
            "tokens_streamed": streamed,
          },
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
      metadata={"results": {"summary": summary}},
    )
    await reporter.send(
      stage="succeeded",
      progress=1.0,
      message=f"Feedback demo complete ({total:0{counter_width}d}/{total:0{counter_width}d})",
      metadata={"results": {"summary": summary}},
    )
  return {"status": "succeeded", "summary": summary, "tokenCount": len(summary)}
