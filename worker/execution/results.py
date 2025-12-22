"""Helpers for building exec result payloads."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, List, Optional

from pydantic import ValidationError

from shared.models.biz.exec.result import Artifact, ExecResultPayload, Status as ResultStatus

from .context import ExecutionContext
from .runner import NodeExecutionResult

LOGGER = logging.getLogger(__name__)


@dataclass
class ExecutionResultBuilder:
    def build(self, context: ExecutionContext, result: NodeExecutionResult, *, duration_ms: int) -> ExecResultPayload:
        metadata_payload: dict[str, Any] = {}
        if context.metadata:
            metadata_payload.update(context.metadata)
        if result.metadata:
            metadata_payload.update(result.metadata)
        return ExecResultPayload(
            run_id=context.run_id,
            task_id=context.task_id,
            status=self._normalise_result_status(result.status),
            result=result.outputs,
            duration_ms=duration_ms,
            metadata=metadata_payload or None,
            artifacts=self._coerce_artifacts(result.artifacts),
        )

    @staticmethod
    def _coerce_artifacts(artifacts: Optional[List[Any]]) -> Optional[List[Artifact]]:
        if not artifacts:
            return None
        coerced: List[Artifact] = []
        for entry in artifacts:
            if isinstance(entry, Artifact):
                coerced.append(entry)
                continue
            try:
                coerced.append(Artifact.model_validate(entry))
            except ValidationError as exc:  # noqa: BLE001
                LOGGER.warning("Dropping invalid artifact descriptor %s: %s", entry, exc)
        return coerced or None

    @staticmethod
    def _normalise_result_status(status: str) -> ResultStatus:
        if not status:
            LOGGER.warning("Adapter returned empty status; defaulting to FAILED")
            return ResultStatus.FAILED
        upper = status.upper()
        mapping = {
            "SUCCESS": ResultStatus.SUCCEEDED.value,
            "SUCCEED": ResultStatus.SUCCEEDED.value,
            "SUCCEEDED": ResultStatus.SUCCEEDED.value,
            "ALLOWED": ResultStatus.SUCCEEDED.value,
            "BLOCKED": ResultStatus.SUCCEEDED.value,
            "OK": ResultStatus.SUCCEEDED.value,
            "DONE": ResultStatus.SUCCEEDED.value,
            "ERROR": ResultStatus.FAILED.value,
            "FAIL": ResultStatus.FAILED.value,
            "FAILED": ResultStatus.FAILED.value,
            "CANCEL": ResultStatus.CANCELLED.value,
            "CANCELLED": ResultStatus.CANCELLED.value,
            "SKIP": ResultStatus.SKIPPED.value,
            "SKIPPED": ResultStatus.SKIPPED.value,
        }
        canonical = mapping.get(upper, upper)
        try:
            return ResultStatus(canonical)
        except ValueError:
            LOGGER.warning("Adapter returned unsupported status '%s'; defaulting to FAILED", status)
        return ResultStatus.FAILED
