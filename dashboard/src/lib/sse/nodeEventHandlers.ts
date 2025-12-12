import type { QueryClient } from "@tanstack/react-query";
import type { NodeStateEvent } from "../../api/models/nodeStateEvent";
import type { NodeResultDeltaEvent } from "../../api/models/nodeResultDeltaEvent";
import type { NodeResultSnapshotEvent } from "../../api/models/nodeResultSnapshotEvent";
import type { NodeErrorEvent } from "../../api/models/nodeErrorEvent";
import {
  applyNodeResultDelta,
  updateRunDefinitionNodeRuntime,
  updateRunDefinitionNodeState,
  updateRunNode,
  updateRunNodeResultDelta,
} from "../sseCache";

export const handleNodeStateCacheUpdate = (
  queryClient: QueryClient,
  payload: NodeStateEvent,
  occurredAt?: string,
) => {
  updateRunNode(queryClient, payload.runId, payload.nodeId, (node) => {
    const next = { ...node };
    if (payload.state?.stage) {
      next.status = payload.state.stage as typeof node.status;
    }
    if (payload.state?.error !== undefined) {
      next.error = payload.state.error ?? null;
    }
    if (payload.state?.message !== undefined) {
      const base =
        next.metadata && typeof next.metadata === "object"
          ? { ...(next.metadata as Record<string, unknown>) }
          : {};
      if (payload.state.message === null) {
        delete (base as Record<string, unknown>).statusMessage;
        delete (base as Record<string, unknown>).message;
        next.metadata = Object.keys(base).length > 0 ? base : null;
      } else {
        (base as Record<string, unknown>).statusMessage = payload.state.message;
        (base as Record<string, unknown>).message = payload.state.message;
        next.metadata = base;
      }
    }
    if (payload.state) {
      next.state = {
        ...payload.state,
        stage: payload.state.stage ?? next.status,
      };
    } else {
      next.state = {
        ...(next.state ?? {}),
        stage: next.status,
      };
    }
    return next;
  });
  updateRunDefinitionNodeState(
    queryClient,
    payload.runId,
    payload.nodeId,
    payload.state ?? null,
    occurredAt
  );
};

export const handleNodeResultDeltaCacheUpdate = (
  queryClient: QueryClient,
  payload: NodeResultDeltaEvent,
) => {
  updateRunNodeResultDelta(queryClient, payload.runId, payload.nodeId, payload);
  applyNodeResultDelta(queryClient, payload.runId, payload.nodeId, payload);
};

export const handleNodeResultSnapshotCacheUpdate = (
  queryClient: QueryClient,
  payload: NodeResultSnapshotEvent,
) => {
  updateRunNode(queryClient, payload.runId, payload.nodeId, (node) => ({
    ...node,
    result: payload.content ?? null,
    artifacts: payload.artifacts ?? node.artifacts ?? null,
  }));
  updateRunDefinitionNodeRuntime(queryClient, payload.runId, payload.nodeId, {
    result: payload.content ?? null,
    artifacts: payload.artifacts ?? null,
    summary: payload.summary ?? null,
  });
};

export const handleNodeErrorCacheUpdate = (
  queryClient: QueryClient,
  payload: NodeErrorEvent,
) => {
  updateRunNode(queryClient, payload.runId, payload.nodeId, (node) => ({
    ...node,
    status: "failed",
    error: payload.error,
    state: {
      ...(node.state ?? {}),
      stage: "failed",
      error: payload.error,
    },
  }));
};
