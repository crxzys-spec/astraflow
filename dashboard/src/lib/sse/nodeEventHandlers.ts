import type { NodeErrorEvent, NodeResultDeltaEvent, NodeResultSnapshotEvent, NodeStateEvent } from "../../client/models";
import { useRunsStore } from "../../store";

export const handleNodeStateStoreUpdate = (
  payload: NodeStateEvent,
) => {
  const store = useRunsStore.getState();
  store.updateRunNode(payload.runId, payload.nodeId, (node) => {
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
};

export const handleNodeResultDeltaStoreUpdate = (payload: NodeResultDeltaEvent) => {
  const store = useRunsStore.getState();
  store.applyNodeResultDelta(payload.runId, payload.nodeId, payload);
};

export const handleNodeResultSnapshotStoreUpdate = (payload: NodeResultSnapshotEvent) => {
  const store = useRunsStore.getState();
  const normalizedArtifacts = payload.artifacts
    ? payload.artifacts.map((artifact) => ({ ...(artifact as unknown as Record<string, unknown>) }))
    : undefined;
  store.updateRunNode(payload.runId, payload.nodeId, (node) => ({
    ...node,
    result: payload.content ?? null,
    artifacts: normalizedArtifacts ?? node.artifacts,
  }));
};

export const handleNodeErrorStoreUpdate = (payload: NodeErrorEvent) => {
  const store = useRunsStore.getState();
  store.updateRunNode(payload.runId, payload.nodeId, (node) => ({
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
