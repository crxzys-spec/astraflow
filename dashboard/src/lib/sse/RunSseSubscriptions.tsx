import { useEffect } from "react";
import {
  UiEventType,
  type UiEventEnvelope,
  type RunSnapshotEvent,
  type RunStatusEvent,
} from "../../client/models";
import { useAuthStore } from "@store/authSlice";
import { registerSseHandler } from "./dispatcher";
import { handleRunSnapshotStoreUpdate, handleRunStatusStoreUpdate } from "./runEventHandlers";

/**
 * Global run-level SSE subscriptions.
 * Keeps run list/detail caches fresh regardless of the current page.
 */
export const RunSseSubscriptions = () => {
  const canViewRuns = useAuthStore((state) =>
    state.hasRole(["admin", "run.viewer", "workflow.editor"])
  );

  useEffect(() => {
    if (!canViewRuns) {
      return;
    }

    const handleRunStatus = (event: UiEventEnvelope) => {
      const payload = event.data as RunStatusEvent | undefined;
      if (!payload || payload.kind !== "run.status") {
        return;
      }
      handleRunStatusStoreUpdate(payload, event.occurredAt);
    };

    const handleRunSnapshot = (event: UiEventEnvelope) => {
      const payload = event.data as RunSnapshotEvent | undefined;
      if (!payload || payload.kind !== "run.snapshot") {
        return;
      }
      handleRunSnapshotStoreUpdate(payload);
    };

    const unregisterStatus = registerSseHandler(UiEventType.RunStatus, handleRunStatus);
    const unregisterSnapshot = registerSseHandler(UiEventType.RunSnapshot, handleRunSnapshot);

    return () => {
      unregisterStatus();
      unregisterSnapshot();
    };
  }, [canViewRuns]);

  return null;
};
