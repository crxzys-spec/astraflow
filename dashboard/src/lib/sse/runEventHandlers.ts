import type { QueryClient } from "@tanstack/react-query";
import type { RunStatusEvent } from "../../api/models/runStatusEvent";
import type { RunSnapshotEvent } from "../../api/models/runSnapshotEvent";
import type { RunList } from "../../api/models/runList";
import { getGetRunQueryKey } from "../../api/endpoints";
import { replaceRunSnapshot, updateRunCaches, upsertRunCaches } from "../sseCache";

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
export const handleRunStatusCacheUpdate = (
  queryClient: QueryClient,
  payload: RunStatusEvent,
  occurredAt?: string,
) => {
  const runId = payload.runId;
  const occurredTs = getTimestamp(occurredAt);
  if (occurredTs !== null) {
    const last = statusWatermark.get(runId);
    if (last !== undefined && occurredTs < last) {
      return;
    }
    statusWatermark.set(runId, occurredTs);
  }

  const runKey = getGetRunQueryKey(runId);
  const hasRunDetail = Boolean(queryClient.getQueryData(runKey));
  const matchingLists = queryClient.getQueriesData<RunList>({
    queryKey: ["/api/v1/runs"],
  });
  const hasRunInLists = matchingLists.some(([_key, response]) =>
    (response?.items ?? []).some((item) => item.runId === runId)
  );

  if (!hasRunDetail && !hasRunInLists) {
    upsertRunCaches(queryClient, {
      runId,
      status: payload.status,
      definitionHash: "",
      clientId: "",
      startedAt: payload.startedAt ?? null,
      finishedAt: payload.finishedAt ?? null,
    });
  }

  updateRunCaches(queryClient, runId, (run) => {
    if (run.runId !== runId) {
      return run;
    }
    const next = { ...run, status: payload.status };
    if (payload.startedAt !== undefined) {
      next.startedAt = payload.startedAt ?? null;
    }
    if (payload.finishedAt !== undefined) {
      next.finishedAt = payload.finishedAt ?? null;
    }
    if (payload.status === "failed" && payload.reason) {
      const existingError = (run as { error?: unknown }).error;
      next.error =
        existingError && typeof existingError === "object"
          ? { ...(existingError as Record<string, unknown>), message: payload.reason }
          : { code: "run.failed", message: payload.reason };
    }
    return next;
  });
};

/**
 * Shared handler for run.snapshot events; merges nodes into run cache.
 */
export const handleRunSnapshotCacheUpdate = (
  queryClient: QueryClient,
  payload: RunSnapshotEvent,
) => {
  const snapshotRunId = payload?.run?.runId;
  if (!snapshotRunId) {
    return;
  }
  const combinedRun = {
    ...payload.run,
    nodes: payload.nodes ?? payload.run.nodes,
  };
  replaceRunSnapshot(queryClient, snapshotRunId, combinedRun);
};
