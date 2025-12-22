import type { WorkerHeartbeatEvent, WorkerPackage, WorkerPackageSseEvent } from "../../client/models";
import type { WorkerModel } from "../../services/workers";
import { useWorkersStore } from "../../store/workersSlice";

const getTimestamp = (value?: string | null): number | null => {
  if (!value) {
    return null;
  }
  const parsed = Date.parse(value);
  return Number.isNaN(parsed) ? null : parsed;
};

const mapPackageStatus = (
  status: WorkerPackageSseEvent["status"] | "removing",
): WorkerPackage["status"] => {
  if (status === "removing") {
    return "uninstalling";
  }
  return status;
};

export const handleWorkerHeartbeatStoreUpdate = (payload: WorkerHeartbeatEvent, occurredAt?: string) => {
  const store = useWorkersStore.getState();
  const occurredTs = getTimestamp(occurredAt);
  const heartbeatAt = payload.at ?? occurredAt ?? new Date().toISOString();
  const update: Partial<WorkerModel> & { id: string } = {
    id: payload.workerName,
    lastHeartbeatAt: heartbeatAt,
  };
  if (payload.queues !== undefined) {
    update.queues = payload.queues ?? [];
  }
  if (payload.instanceId !== undefined) {
    update.instanceId = payload.instanceId ?? undefined;
  }
  if (payload.hostname !== undefined) {
    update.hostname = payload.hostname ?? undefined;
  }
  if (payload.version !== undefined) {
    update.version = payload.version ?? undefined;
  }
  if (payload.connected !== undefined && payload.connected !== null) {
    update.connected = payload.connected;
  }
  if (payload.registered !== undefined && payload.registered !== null) {
    update.registered = payload.registered;
  }
  if (payload.heartbeat !== undefined) {
    update.heartbeat = payload.heartbeat ?? undefined;
  }
  store.upsertWorker(update, occurredTs ?? undefined);
};

export const handleWorkerPackageStoreUpdate = (payload: WorkerPackageSseEvent, occurredAt?: string) => {
  const store = useWorkersStore.getState();
  const occurredTs = getTimestamp(occurredAt);
  const updated = {
    name: payload.package,
    version: payload.version ?? undefined,
    status: mapPackageStatus(payload.status),
  };
  const existing = store.byId[payload.workerName];
  if (!existing) {
    store.upsertWorker(
      {
        id: payload.workerName,
        lastHeartbeatAt: new Date().toISOString(),
        queues: [],
        packages: [updated],
      },
      occurredTs ?? undefined,
    );
    return;
  }

  store.updateWorkerPackages(
    payload.workerName,
    (packages) => {
      const next = packages.slice();
      const index = next.findIndex((pkg) => pkg.name === payload.package);
      if (index >= 0) {
        next[index] = { ...next[index], ...updated };
      } else {
        next.push(updated);
      }
      return next;
    },
    occurredTs ?? undefined,
  );
};
