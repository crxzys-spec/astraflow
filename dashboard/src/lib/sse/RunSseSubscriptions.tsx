import { useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";
import type { UiEventEnvelope } from "../../api/models/uiEventEnvelope";
import { UiEventType } from "../../api/models/uiEventType";
import type { RunStatusEvent } from "../../api/models/runStatusEvent";
import type { RunSnapshotEvent } from "../../api/models/runSnapshotEvent";
import { useAuthStore } from "../../features/auth/store";
import { registerSseHandler } from "./dispatcher";
import { handleRunSnapshotCacheUpdate, handleRunStatusCacheUpdate } from "./runEventHandlers";

/**
 * Global run-level SSE subscriptions.
 * Keeps run list/detail caches fresh regardless of the current page.
 */
export const RunSseSubscriptions = () => {
  const queryClient = useQueryClient();
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
      handleRunStatusCacheUpdate(queryClient, payload, event.occurredAt);
    };

    const handleRunSnapshot = (event: UiEventEnvelope) => {
      const payload = event.data as RunSnapshotEvent | undefined;
      if (!payload || payload.kind !== "run.snapshot") {
        return;
      }
      handleRunSnapshotCacheUpdate(queryClient, payload);
    };

    const unregisterStatus = registerSseHandler(UiEventType.runstatus, handleRunStatus);
    const unregisterSnapshot = registerSseHandler(UiEventType.runsnapshot, handleRunSnapshot);

    return () => {
      unregisterStatus();
      unregisterSnapshot();
    };
  }, [canViewRuns, queryClient]);

  return null;
};
