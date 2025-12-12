import { useEffect, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { UiEventType } from "../api/models/uiEventType";
import type { UiEventEnvelope } from "../api/models/uiEventEnvelope";
import type { RunStatusEvent } from "../api/models/runStatusEvent";
import type { RunSnapshotEvent } from "../api/models/runSnapshotEvent";
import type { NodeStateEvent } from "../api/models/nodeStateEvent";
import type { NodeResultDeltaEvent } from "../api/models/nodeResultDeltaEvent";
import type { NodeResultSnapshotEvent } from "../api/models/nodeResultSnapshotEvent";
import type { NodeErrorEvent } from "../api/models/nodeErrorEvent";
import type { RunStatus } from "../api/models/runStatus";
import {
  applyRunDefinitionSnapshot,
} from "../lib/sseCache";
import { registerSseHandler } from "../lib/sse/dispatcher";
import {
  handleNodeErrorCacheUpdate,
  handleNodeResultDeltaCacheUpdate,
  handleNodeResultSnapshotCacheUpdate,
  handleNodeStateCacheUpdate,
} from "../lib/sse/nodeEventHandlers";

type RunMessage =
  | { type: "success"; runId?: string; text: string }
  | { type: "error"; text: string };

type UseRunSseSyncOptions = {
  activeRunId?: string;
  activeRunStatus?: RunStatus;
  onActiveRunChange?: (runId: string) => void;
  onRunStatusChange?: (status: RunStatus) => void;
  onRunMessage?: (message: RunMessage) => void;
  enabled?: boolean;
};

const extractRunId = (event: UiEventEnvelope): string | undefined => {
  const scopeRunId = event.scope?.runId;
  const data = event.data as Record<string, unknown> | undefined;
  if (!data) {
    return scopeRunId;
  }
  if (typeof data.runId === "string") {
    return data.runId;
  }
  const run = data.run as { runId?: unknown } | undefined;
  if (run && typeof run.runId === "string") {
    return run.runId;
  }
  return scopeRunId;
};

const isFinalStatus = (status?: RunStatus) =>
  status === "succeeded" || status === "failed" || status === "cancelled";

export const useRunSseSync = ({
  activeRunId,
  activeRunStatus,
  onActiveRunChange,
  onRunStatusChange,
  onRunMessage,
  enabled = true,
}: UseRunSseSyncOptions) => {
  const queryClient = useQueryClient();
  const activeRunRef = useRef<string | undefined>(activeRunId);
  const activeRunStatusRef = useRef<RunStatus | undefined>(activeRunStatus);

  useEffect(() => {
    activeRunRef.current = activeRunId;
  }, [activeRunId]);

  useEffect(() => {
    activeRunStatusRef.current = activeRunStatus;
  }, [activeRunStatus]);

  useEffect(() => {
    if (!enabled) {
      return;
    }
    const matchesActiveRun = (event: UiEventEnvelope, runId?: string) => {
      const currentRunId = activeRunRef.current;
      if (!currentRunId || !runId) {
        return false;
      }
      const derivedRunId = extractRunId(event);
      if ((derivedRunId && derivedRunId !== currentRunId) || runId !== currentRunId) {
        return false;
      }
      if (event.scope?.runId && event.scope.runId !== currentRunId) {
        return false;
      }
      return true;
    };

    const handleRunStatus = (event: UiEventEnvelope) => {
      const payload = event.data as RunStatusEvent | undefined;
      if (!payload || payload.kind !== "run.status") {
        return;
      }

      let currentRunId = activeRunRef.current;

      const activeStatus = activeRunStatusRef.current;
      const shouldFollow =
        payload.runId &&
        (!currentRunId || payload.runId === currentRunId || isFinalStatus(activeStatus));

      if (shouldFollow && payload.runId !== currentRunId) {
        activeRunRef.current = payload.runId;
        currentRunId = payload.runId;
        onActiveRunChange?.(payload.runId);
      }

      if (!matchesActiveRun(event, currentRunId)) {
        return;
      }

      const status = payload.status as RunStatus;
      activeRunStatusRef.current = status;
      const readableStatus = status
        .replace(/[_-]+/g, " ")
        .replace(/^\w/, (char) => char.toUpperCase());
      const messageSuffix = payload.reason ? ` (${payload.reason})` : "";
      onRunStatusChange?.(status);
      onRunMessage?.({
        type: status === "failed" || status === "cancelled" ? "error" : "success",
        runId: payload.runId,
        text: `Run ${payload.runId} ${readableStatus}${messageSuffix}`,
      });
    };

    const handleRunSnapshot = (event: UiEventEnvelope) => {
      const payload = event.data as RunSnapshotEvent | undefined;
      const snapshotRunId = payload?.run?.runId;
      if (!payload || payload.kind !== "run.snapshot" || !snapshotRunId) {
        return;
      }
      if (!matchesActiveRun(event, snapshotRunId)) {
        return;
      }
      applyRunDefinitionSnapshot(queryClient, snapshotRunId, payload.nodes ?? undefined, event.occurredAt);
    };

    const handleNodeState = (event: UiEventEnvelope) => {
      const payload = event.data as NodeStateEvent | undefined;
      if (!payload || payload.kind !== "node.state" || !matchesActiveRun(event, payload.runId)) {
        return;
      }
      handleNodeStateCacheUpdate(queryClient, payload, event.occurredAt);
    };

    const handleNodeResultDelta = (event: UiEventEnvelope) => {
      const payload = event.data as NodeResultDeltaEvent | undefined;
      if (!payload || payload.kind !== "node.result.delta" || !matchesActiveRun(event, payload.runId)) {
        return;
      }
      handleNodeResultDeltaCacheUpdate(queryClient, payload);
    };

    const handleNodeResultSnapshot = (event: UiEventEnvelope) => {
      const payload = event.data as NodeResultSnapshotEvent | undefined;
      if (
        !payload ||
        payload.kind !== "node.result.snapshot" ||
        !matchesActiveRun(event, payload.runId)
      ) {
        return;
      }
      handleNodeResultSnapshotCacheUpdate(queryClient, payload);
    };

    const handleNodeError = (event: UiEventEnvelope) => {
      const payload = event.data as NodeErrorEvent | undefined;
      if (!payload || payload.kind !== "node.error" || !matchesActiveRun(event, payload.runId)) {
        return;
      }
      handleNodeErrorCacheUpdate(queryClient, payload);
    };

    const unregister = [
      registerSseHandler(UiEventType.runstatus, handleRunStatus),
      registerSseHandler(UiEventType.runsnapshot, handleRunSnapshot),
      registerSseHandler(UiEventType.nodestate, handleNodeState),
      registerSseHandler(UiEventType.noderesultdelta, handleNodeResultDelta),
      registerSseHandler(UiEventType.noderesultsnapshot, handleNodeResultSnapshot),
      registerSseHandler(UiEventType.nodeerror, handleNodeError),
    ];

    return () => {
      unregister.forEach((fn) => fn());
    };
  }, [enabled, onActiveRunChange, onRunMessage, onRunStatusChange, queryClient]);
};
