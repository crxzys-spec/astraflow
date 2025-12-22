import { useEffect } from "react";
import {
  UiEventType,
  type UiEventEnvelope,
  type WorkerHeartbeatEvent,
  type WorkerPackageSseEvent,
} from "../../client/models";
import { useAuthStore } from "@store/authSlice";
import { registerSseHandler } from "./dispatcher";
import { handleWorkerHeartbeatStoreUpdate, handleWorkerPackageStoreUpdate } from "./workerEventHandlers";

/**
 * Global worker SSE subscriptions.
 * Keeps worker caches fresh while the admin console is open.
 */
export const WorkerSseSubscriptions = () => {
  const canViewWorkers = useAuthStore((state) => state.hasRole(["admin", "run.viewer"]));

  useEffect(() => {
    if (!canViewWorkers) {
      return;
    }

    const handleHeartbeat = (event: UiEventEnvelope) => {
      const payload = event.data as WorkerHeartbeatEvent | undefined;
      if (!payload || payload.kind !== "worker.heartbeat") {
        return;
      }
      handleWorkerHeartbeatStoreUpdate(payload, event.occurredAt);
    };

    const handlePackage = (event: UiEventEnvelope) => {
      const payload = event.data as WorkerPackageSseEvent | undefined;
      if (!payload || payload.kind !== "worker.package") {
        return;
      }
      handleWorkerPackageStoreUpdate(payload, event.occurredAt);
    };

    const unregisterHeartbeat = registerSseHandler(UiEventType.WorkerHeartbeat, handleHeartbeat);
    const unregisterPackage = registerSseHandler(UiEventType.WorkerPackage, handlePackage);

    return () => {
      unregisterHeartbeat();
      unregisterPackage();
    };
  }, [canViewWorkers]);

  return null;
};
