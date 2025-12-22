import { useCallback, useEffect, useMemo } from "react";
import { create } from "zustand";
import { immer } from "zustand/middleware/immer";
import { toApiError, type ApiError } from "../api/fetcher";
import type { WorkerCommand, WorkerPackage, WorkerPackageStatus } from "../client/models";
import type { WorkerModel, WorkerQueryParams } from "../services/workers";
import { normalizeWorker, workersGateway } from "../services/workers";
import { buildKey, isCacheFresh, type ResourceStatus } from "./shared";

type WorkersQueryParamsNormalized = {
  queue: string | null;
  connected: boolean | null;
  registered: boolean | null;
  healthy: boolean | null;
  packageName: string | null;
  packageVersion: string | null;
  packageStatus: WorkerPackageStatus | null;
  maxHeartbeatAgeSeconds: number | null;
  maxInflight: number | null;
  maxLatencyMs: number | null;
  limit: number | null;
  cursor: string | null;
};

type WorkerMeta = {
  status: ResourceStatus;
  error: ApiError | null;
  updatedAt?: number;
  staleAfter: number;
};

type WorkerListState = {
  key: string;
  params: WorkersQueryParamsNormalized;
  ids: string[];
  nextCursor?: string | null;
  status: ResourceStatus;
  error: ApiError | null;
  updatedAt?: number;
  staleAfter: number;
};

type WorkersState = {
  byId: Record<string, WorkerModel>;
  metaById: Record<string, WorkerMeta>;
  lists: Record<string, WorkerListState>;
  fetchWorkers: (params?: WorkerQueryParams, options?: { force?: boolean; staleAfter?: number }) => Promise<WorkerModel[]>;
  getWorker: (workerId: string, options?: { force?: boolean; staleAfter?: number }) => Promise<WorkerModel | null>;
  sendWorkerCommand: (workerId: string, command: WorkerCommand, idempotencyKey?: string) => Promise<void>;
  upsertWorker: (worker: Partial<WorkerModel> & { id: string }, updatedAt?: number) => void;
  updateWorkerPackages: (
    workerId: string,
    updater: (packages: WorkerPackage[]) => WorkerPackage[],
    updatedAt?: number,
  ) => void;
};

const DEFAULT_LIST_STALE_MS = 20_000;
const DEFAULT_WORKER_STALE_MS = 20_000;

const listIsUnfiltered = (list: WorkerListState): boolean => {
  const { params } = list;
  return (
    params.queue === null &&
    params.connected === null &&
    params.registered === null &&
    params.healthy === null &&
    params.packageName === null &&
    params.packageVersion === null &&
    params.packageStatus === null &&
    params.maxHeartbeatAgeSeconds === null &&
    params.maxInflight === null &&
    params.maxLatencyMs === null
  );
};

const addWorkerToList = (list: WorkerListState, workerId: string) => {
  const nextIds = [workerId, ...list.ids.filter((id) => id !== workerId)];
  const limit = list.params.limit;
  if (typeof limit === "number" && limit > 0 && nextIds.length > limit) {
    list.ids = nextIds.slice(0, limit);
  } else {
    list.ids = nextIds;
  }
};

const buildParamsKey = (
  params?: WorkerQueryParams,
): { key: string; normalized: WorkersQueryParamsNormalized } => {
  const normalized: WorkersQueryParamsNormalized = {
    queue: params?.queue ?? null,
    connected: params?.connected ?? null,
    registered: params?.registered ?? null,
    healthy: params?.healthy ?? null,
    packageName: params?.packageName ?? null,
    packageVersion: params?.packageVersion ?? null,
    packageStatus: params?.packageStatus ?? null,
    maxHeartbeatAgeSeconds: params?.maxHeartbeatAgeSeconds ?? null,
    maxInflight: params?.maxInflight ?? null,
    maxLatencyMs: params?.maxLatencyMs ?? null,
    limit: params?.limit ?? null,
    cursor: params?.cursor ?? null,
  };
  const key = buildKey(
    normalized.queue,
    normalized.connected,
    normalized.registered,
    normalized.healthy,
    normalized.packageName,
    normalized.packageVersion,
    normalized.packageStatus,
    normalized.maxHeartbeatAgeSeconds,
    normalized.maxInflight,
    normalized.maxLatencyMs,
    normalized.limit,
    normalized.cursor,
  );
  return { key, normalized };
};

const initialMeta = (staleAfter: number): WorkerMeta => ({
  status: "idle",
  error: null,
  staleAfter,
});

export const useWorkersStore = create<WorkersState>()(
  immer((set, get) => ({
    byId: {},
    metaById: {},
    lists: {},

    fetchWorkers: async (params, options) => {
      const { key, normalized } = buildParamsKey(params);
      const now = Date.now();
      const currentList = get().lists[key];
      const staleAfter = options?.staleAfter ?? currentList?.staleAfter ?? DEFAULT_LIST_STALE_MS;

      if (currentList?.status === "success" && isCacheFresh(currentList.updatedAt, staleAfter, now, options?.force)) {
        return currentList.ids
          .map((id) => get().byId[id])
          .filter((worker): worker is WorkerModel => Boolean(worker));
      }

      set((state) => {
        const next = state.lists[key] ?? {
          key,
          params: normalized,
          ids: [],
          nextCursor: null,
          status: "idle" as ResourceStatus,
          error: null,
          staleAfter,
        };
        next.status = "loading";
        next.error = null;
        next.staleAfter = staleAfter;
        state.lists[key] = next;
      });

      try {
        const payload = await workersGateway.list(params);
        const items = payload.items;
        set((state) => {
          items.forEach((worker) => {
            state.byId[worker.id] = worker;
            state.metaById[worker.id] = {
              ...(state.metaById[worker.id] ?? initialMeta(DEFAULT_WORKER_STALE_MS)),
              status: "success",
              error: null,
              updatedAt: now,
              staleAfter: DEFAULT_WORKER_STALE_MS,
            };
          });
          const next = state.lists[key]!;
          next.ids = items.map((worker) => worker.id);
          next.nextCursor = payload.nextCursor ?? null;
          next.status = "success";
          next.error = null;
          next.updatedAt = now;
          next.staleAfter = staleAfter;
        });
        return items;
      } catch (error) {
        const apiError = toApiError(error);
        set((state) => {
          const next = state.lists[key]!;
          next.status = "error";
          next.error = apiError;
          next.updatedAt = now;
        });
        throw apiError;
      }
    },

    getWorker: async (workerId, options) => {
      if (!workerId) {
        return null;
      }
      const now = Date.now();
      const existing = get().byId[workerId];
      const meta = get().metaById[workerId];
      const staleAfter = options?.staleAfter ?? meta?.staleAfter ?? DEFAULT_WORKER_STALE_MS;
      if (existing && meta?.status === "success" && isCacheFresh(meta.updatedAt, staleAfter, now, options?.force)) {
        return existing;
      }

      set((state) => {
        state.metaById[workerId] = {
          ...(state.metaById[workerId] ?? initialMeta(staleAfter)),
          status: "loading",
          error: null,
          staleAfter,
        };
      });

      try {
        const worker = await workersGateway.get(workerId);
        set((state) => {
          state.byId[workerId] = worker;
          state.metaById[workerId] = {
            ...(state.metaById[workerId] ?? initialMeta(staleAfter)),
            status: "success",
            error: null,
            updatedAt: now,
            staleAfter,
          };
        });
        return worker;
      } catch (error) {
        const apiError = toApiError(error);
        set((state) => {
          state.metaById[workerId] = {
            ...(state.metaById[workerId] ?? initialMeta(staleAfter)),
            status: "error",
            error: apiError,
            updatedAt: now,
            staleAfter,
          };
        });
        throw apiError;
      }
    },

    sendWorkerCommand: async (workerId, command, idempotencyKey) => {
      await workersGateway.command(workerId, command, idempotencyKey);
    },

    upsertWorker: (worker, updatedAt) => {
      const timestamp = updatedAt ?? Date.now();
      set((state) => {
        const existing = state.byId[worker.id];
        const merged = normalizeWorker({
          ...(existing ?? { id: worker.id, lastHeartbeatAt: new Date().toISOString(), queues: [] }),
          ...worker,
          id: worker.id,
        });
        state.byId[worker.id] = merged;
        state.metaById[worker.id] = {
          ...(state.metaById[worker.id] ?? initialMeta(DEFAULT_WORKER_STALE_MS)),
          status: "success",
          error: null,
          updatedAt: timestamp,
        };
        Object.values(state.lists).forEach((list) => {
          if (list.ids.includes(worker.id)) {
            return;
          }
          if (listIsUnfiltered(list)) {
            addWorkerToList(list, worker.id);
          }
        });
      });
    },

    updateWorkerPackages: (workerId, updater, updatedAt) => {
      const timestamp = updatedAt ?? Date.now();
      set((state) => {
        const existing = state.byId[workerId];
        if (!existing) {
          return;
        }
        const nextPackages = updater(existing.packages ?? []);
        state.byId[workerId] = { ...existing, packages: nextPackages };
        state.metaById[workerId] = {
          ...(state.metaById[workerId] ?? initialMeta(DEFAULT_WORKER_STALE_MS)),
          status: "success",
          error: null,
          updatedAt: timestamp,
        };
      });
    },
  })),
);

export const useWorkers = (params?: WorkerQueryParams, options?: { enabled?: boolean }) => {
  const enabled = options?.enabled ?? true;
  const { key } = useMemo(
    () => buildParamsKey(params),
    [
      params?.queue,
      params?.connected,
      params?.registered,
      params?.healthy,
      params?.packageName,
      params?.packageVersion,
      params?.packageStatus,
      params?.maxHeartbeatAgeSeconds,
      params?.maxInflight,
      params?.maxLatencyMs,
      params?.limit,
      params?.cursor,
    ],
  );
  const list = useWorkersStore((state) => state.lists[key]);
  const byId = useWorkersStore((state) => state.byId);
  const fetchList = useWorkersStore((state) => state.fetchWorkers);

  useEffect(() => {
    if (enabled) {
      fetchList(params);
    }
  }, [enabled, fetchList, key]);

  const items = useMemo(
    () => list?.ids.map((id) => byId[id]).filter((worker): worker is WorkerModel => Boolean(worker)) ?? [],
    [byId, list?.ids],
  );
  const selected = useMemo(
    () => ({
      items,
      nextCursor: list?.nextCursor ?? null,
      status: list?.status ?? ("idle" as ResourceStatus),
      error: list?.error ?? null,
    }),
    [items, list?.error, list?.nextCursor, list?.status],
  );

  const refetch = useCallback(
    () => (enabled ? fetchList(params, { force: true }) : Promise.resolve([])),
    [enabled, fetchList, key],
  );

  return {
    ...selected,
    isLoading: selected.status === "loading",
    isError: selected.status === "error",
    refetch,
  };
};

export const useWorker = (workerId?: string) => {
  const worker = useWorkersStore((state) => (workerId ? state.byId[workerId] : undefined));
  const meta = useWorkersStore((state) => (workerId ? state.metaById[workerId] : undefined));
  const getWorker = useWorkersStore((state) => state.getWorker);

  useEffect(() => {
    if (workerId) {
      void getWorker(workerId);
    }
  }, [getWorker, workerId]);

  const selected = useMemo(
    () => ({
      worker: worker ?? null,
      status: meta?.status ?? ("idle" as ResourceStatus),
      error: meta?.error ?? null,
    }),
    [meta?.error, meta?.status, worker],
  );

  const refetch = useCallback(
    () => (workerId ? getWorker(workerId, { force: true }) : Promise.resolve(null)),
    [getWorker, workerId],
  );

  return {
    ...selected,
    isLoading: selected.status === "loading",
    isError: selected.status === "error",
    refetch,
  };
};
