"""System adapter handlers (container + middleware utilities)."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List

from worker.execution import ExecutionContext

LOGGER = logging.getLogger(__name__)


async def container(context: ExecutionContext) -> Dict[str, Any]:  # pragma: no cover - scheduler-handled
    """Placeholder for container nodes; actual orchestration runs in the scheduler."""
    LOGGER.warning(
        "container handler invoked on worker (run=%s node=%s); this node should be handled by scheduler",
        context.run_id,
        context.node_id,
    )
    return {"status": "failed", "error": "container node is not executable on worker"}


def _as_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _as_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _extract_resource_list(value: Any) -> List[Dict[str, Any]]:
    if isinstance(value, list):
        return [entry for entry in value if isinstance(entry, dict)]
    if isinstance(value, dict):
        return [value]
    return []


async def loop_middleware(context: ExecutionContext) -> Dict[str, Any]:
    """Middleware that invokes the next handler multiple times."""
    params = context.params or {}
    times = max(1, _as_int(params.get("times", 1), 1))
    delay_ms = max(0.0, _as_float(params.get("delayMs", 0), 0.0))
    stop_on_error = bool(params.get("stopOnError", True))

    responses: List[Dict[str, Any]] = []
    failures: List[Dict[str, Any]] = []
    iterations = 0

    for idx in range(times):
        
        iterations += 1
        iteration_ctx = {"iteration": iterations}
        try:
            result = await context.next(
                {"iteration": iterations},
                middleware_ctx=iteration_ctx,
            )
            responses.append(result)
        except Exception as exc:  # noqa: BLE001
            LOGGER.warning(
                "loop middleware iteration %s failed run=%s node=%s error=%s",
                iterations,
                context.run_id,
                context.node_id,
                exc,
            )
            failures.append({"iteration": iterations, "error": str(exc)})
            if stop_on_error:
                break
        # Emit lightweight feedback so UI can display current iteration
        try:
            if context.feedback:
                progress = iterations / times if times > 0 else None
                await context.feedback.send(
                    progress=progress,
                    metadata={"results": {"iterations": iterations}},
                )
        except Exception:  # noqa: BLE001
            LOGGER.debug("loop middleware feedback send failed run=%s node=%s", context.run_id, context.node_id)
        if delay_ms > 0 and idx < times - 1:
            await asyncio.sleep(delay_ms / 1000.0)

    succeeded = iterations - len(failures)
    status = "succeeded" if not failures else "failed"
    return {
        "status": status,
        "iterations": iterations,
        "succeeded": succeeded,
        "failures": failures,
        "responses": responses,
    }


async def input_generator(context: ExecutionContext) -> Dict[str, Any]:
    """Emit a value parsed according to the requested type for quick testing."""

    params = context.params or {}
    kind = str(params.get("type") or "string").lower().strip()
    raw_value = params.get("value")

    parsed = raw_value
    if kind == "number":
        try:
            parsed = int(raw_value)
        except Exception:
            parsed = None
    elif kind == "float":
        try:
            parsed = float(raw_value)
        except Exception:
            parsed = None
    elif kind == "boolean":
        if isinstance(raw_value, bool):
            parsed = raw_value
        else:
            parsed = str(raw_value).strip().lower() in {"true", "1", "yes", "on"}
    elif kind in {"string", "text", "textarea"}:
        parsed = "" if raw_value is None else str(raw_value)

    return {
        "status": "succeeded",
        "type": kind,
        "raw": raw_value,
        "value": parsed,
    }


async def upload_test(context: ExecutionContext) -> Dict[str, Any]:
    """Echo uploaded resource metadata for the file-upload widget."""

    params = context.params or {}
    resources = _extract_resource_list(params.get("resources"))
    if not resources:
        resources = _extract_resource_list(params.get("resource"))

    resource_ids: List[str] = []
    filenames: List[str] = []
    sizes: List[int] = []
    for entry in resources:
        resource_id = entry.get("resourceId") or entry.get("resource_id") or entry.get("id")
        if resource_id:
            resource_ids.append(str(resource_id))
        filename = entry.get("filename") or entry.get("name")
        if filename:
            filenames.append(str(filename))
        size = entry.get("sizeBytes") or entry.get("size_bytes")
        if isinstance(size, (int, float)):
            sizes.append(int(size))

    return {
        "status": "succeeded",
        "outputs": {
            "count": len(resources),
            "resourceIds": resource_ids,
            "filenames": filenames,
            "sizes": sizes,
            "resources": resources,
        },
    }


async def case_middleware(context: ExecutionContext) -> Dict[str, Any]:
    """Short-circuit middleware chain when disabled."""

    params = context.params or {}
    enabled = bool(params.get("enabled", True))
    if not enabled:
        return {"status": "skipped", "enabled": False, "skipped": True, "metadata": {"stage": "skipped"}}

    next_result = await context.next()
    payload: Dict[str, Any] = {"status": "succeeded", "enabled": True, "skipped": False}
    if isinstance(next_result, dict):
        payload.update(next_result)
    else:
        payload["result"] = next_result
    return payload
