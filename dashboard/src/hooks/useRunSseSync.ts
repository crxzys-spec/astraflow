import { useEffect, useRef } from "react";
import type { RunStatusModel } from "../services/runs";
import {
  UiEventType,
  type UiEventEnvelope,
  type RunStatusEvent,
  type RunSnapshotEvent,
  type NodeStateEvent,
  type NodeResultDeltaEvent,
  type NodeResultSnapshotEvent,
  type NodeErrorEvent,
} from "../client/models";
import { registerSseHandler } from "../lib/sse/dispatcher";
import {
  handleNodeErrorStoreUpdate,
  handleNodeResultDeltaStoreUpdate,
  handleNodeResultSnapshotStoreUpdate,
  handleNodeStateStoreUpdate,
} from "../lib/sse/nodeEventHandlers";
import { handleRunSnapshotStoreUpdate, handleRunStatusStoreUpdate } from "../lib/sse/runEventHandlers";

type RunMessage =
  | { type: "success"; runId?: string; text: string }
  | { type: "error"; text: string };

type UseRunSseSyncOptions = {
  activeRunId?: string;
  activeRunStatus?: RunStatusModel;
  onActiveRunChange?: (runId: string) => void;
  onRunStatusChange?: (status: RunStatusModel) => void;
  onRunMessage?: (message: RunMessage) => void;
  enabled?: boolean;
};

const extractRunId = (event: UiEventEnvelope): string | undefined => {
  const scopeRunId = event.scope?.runId ?? undefined;
  const data = event.data as any;
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

const isFinalStatus = (status?: RunStatusModel) =>
  status === "succeeded" || status === "failed" || status === "cancelled";

export const useRunSseSync = ({
  activeRunId,
  activeRunStatus,
  onActiveRunChange,
  onRunStatusChange,
  onRunMessage,
  enabled = true,
}: UseRunSseSyncOptions) => {
  const activeRunRef = useRef<string | undefined>(activeRunId);
  const activeRunStatusRef = useRef<RunStatusModel | undefined>(activeRunStatus);

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

      const status = payload.status as RunStatusModel;
      activeRunStatusRef.current = status;
      handleRunStatusStoreUpdate(payload, event.occurredAt);
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
      handleRunSnapshotStoreUpdate(payload);
    };

    const handleNodeState = (event: UiEventEnvelope) => {
      const payload = event.data as NodeStateEvent | undefined;
      if (!payload || payload.kind !== "node.state" || !matchesActiveRun(event, payload.runId)) {
        return;
      }
      handleNodeStateStoreUpdate(payload);
    };

    const handleNodeResultDelta = (event: UiEventEnvelope) => {
      const payload = event.data as NodeResultDeltaEvent | undefined;
      if (!payload || payload.kind !== "node.result.delta" || !matchesActiveRun(event, payload.runId)) {
        return;
      }
      handleNodeResultDeltaStoreUpdate(payload);
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
      handleNodeResultSnapshotStoreUpdate(payload);
    };

    const handleNodeError = (event: UiEventEnvelope) => {
      const payload = event.data as NodeErrorEvent | undefined;
      if (!payload || payload.kind !== "node.error" || !matchesActiveRun(event, payload.runId)) {
        return;
      }
      handleNodeErrorStoreUpdate(payload);
    };

    const unregister = [
      registerSseHandler(UiEventType.RunStatus, handleRunStatus),
      registerSseHandler(UiEventType.RunSnapshot, handleRunSnapshot),
      registerSseHandler(UiEventType.NodeState, handleNodeState),
      registerSseHandler(UiEventType.NodeResultDelta, handleNodeResultDelta),
      registerSseHandler(UiEventType.NodeResultSnapshot, handleNodeResultSnapshot),
      registerSseHandler(UiEventType.NodeError, handleNodeError),
    ];

    return () => {
      unregister.forEach((fn) => fn());
    };
  }, [enabled, onActiveRunChange, onRunMessage, onRunStatusChange]);
};
