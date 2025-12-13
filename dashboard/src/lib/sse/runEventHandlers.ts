import type { RunSnapshotEvent, RunStatusEvent } from "../../client/models";
import { useRunsStore } from "../../store";
import { normalizeRun, type RunModel } from "../../services/runs";

const statusWatermark = new Map<string, number>();

const getTimestamp = (value?: string | null): number | null => {
  if (!value) {
    return null;
  }
  const parsed = Date.parse(value);
  return Number.isNaN(parsed) ? null : parsed;
};

/**
 * Shared handler for run.status events that normalizes cache updates.
 * Keeps list/detail caches in sync and enriches failed runs with reason text.
 */
export const handleRunStatusStoreUpdate = (payload: RunStatusEvent, occurredAt?: string) => {
  const store = useRunsStore.getState();
  const runId = payload.runId;
  const occurredTs = getTimestamp(occurredAt);
  if (occurredTs !== null) {
    const last = statusWatermark.get(runId);
    if (last !== undefined && occurredTs < last) {
      return;
    }
    statusWatermark.set(runId, occurredTs);
  }

  store.updateRunStatus(runId, payload.status, {
    startedAt: payload.startedAt ?? undefined,
    finishedAt: payload.finishedAt ?? undefined,
    error:
      payload.status === "failed" && payload.reason
        ? { message: payload.reason, code: "run.failed" }
        : undefined,
  }, occurredTs ?? undefined);
};

/**
 * Shared handler for run.snapshot events; merges nodes into run cache.
 */
export const handleRunSnapshotStoreUpdate = (payload: RunSnapshotEvent) => {
  const store = useRunsStore.getState();
  const snapshotRunId = payload?.run?.runId;
  if (!snapshotRunId) {
    return;
  }
  const nodes = payload.nodes ?? payload.run.nodes ?? [];
  const combinedRun: RunModel = normalizeRun({
    ...payload.run,
    nodes,
  });
  store.mergeRunSnapshot(combinedRun, nodes);
};
