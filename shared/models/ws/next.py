from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class NextRequestPayload(BaseModel):
    """Middleware next request sent from worker to scheduler."""

    request_id: str = Field(alias="requestId")
    run_id: str = Field(alias="runId")
    node_id: str = Field(alias="nodeId")
    middleware_id: str = Field(alias="middlewareId")
    chain_index: Optional[int] = Field(default=None, alias="chainIndex")
    host_ctx: Optional[Dict[str, Any]] = Field(default=None, alias="hostCtx")
    middleware_ctx: Optional[Dict[str, Any]] = Field(default=None, alias="middlewareCtx")
    payload: Optional[Dict[str, Any]] = None
    timeout_ms: Optional[int] = Field(default=None, alias="timeoutMs")


class NextResponsePayload(BaseModel):
    """Middleware next response sent from scheduler to worker."""

    request_id: str = Field(alias="requestId")
    run_id: str = Field(alias="runId")
    node_id: str = Field(alias="nodeId")
    middleware_id: str = Field(alias="middlewareId")
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None
    trace: Optional[Dict[str, Any]] = None
