import { useCallback, useEffect, useMemo } from "react";
import { create } from "zustand";
import { immer } from "zustand/middleware/immer";
import { toApiError, type ApiError } from "../api/fetcher";
import { applyResultDelta } from "../lib/utils/jsonDelta";
import type { NodeResultDeltaEvent, RunNodeStatus, RunStatus } from "../client/models";
import type { RunDefinitionModel, RunModel, RunStartPayload } from "../services/runs";
import { runsGateway, normalizeRun } from "../services/runs";
import { buildKey, isCacheFresh, type ResourceStatus } from "./shared";

type RunNodeStatusModel = RunNodeStatus;
type NodeResultDeltaModel = NodeResultDeltaEvent;

export type RunsQueryParams = {
  limit?: number;
  cursor?: string;
  status?: RunStatus;
  clientId?: string;
};

type RunsQueryParamsNormalized = {
  limit: number | null;
  cursor: string | null;
  status: RunStatus | null;
  clientId: string | null;
};

type RunMeta = {
  status: ResourceStatus;
  error: ApiError | null;
  updatedAt?: number;
  staleAfter: number;
};

type RunListState = {
  key: string;
  params: RunsQueryParamsNormalized;
  ids: string[];
  nextCursor?: string | null;
  status: ResourceStatus;
  error: ApiError | null;
  updatedAt?: number;
  staleAfter: number;
};

type RunDefinitionState = {
  runId: string;
  data?: RunDefinitionModel | null;
  status: ResourceStatus;
  error: ApiError | null;
  updatedAt?: number;
  staleAfter: number;
};

type RunsState = {
  byId: Record<string, RunModel>;
  metaById: Record<string, RunMeta>;
  lists: Record<string, RunListState>;
  definitions: Record<string, RunDefinitionState>;
  fetchRuns: (params?: RunsQueryParams, options?: { force?: boolean; staleAfter?: number }) => Promise<RunModel[]>;
  getRun: (runId: string, options?: { force?: boolean; staleAfter?: number }) => Promise<RunModel | null>;
  getRunDefinition: (
    runId: string,
    options?: { force?: boolean; staleAfter?: number },
  ) => Promise<RunDefinitionModel | null>;
  startRun: (payload: RunStartPayload, options?: { idempotencyKey?: string }) => Promise<RunModel>;
  cancelRun: (runId: string) => Promise<void>;
  upsertRun: (run: Partial<RunModel> & { runId: string }, updatedAt?: number) => void;
  mergeRunSnapshot: (run: RunModel, nodes?: RunNodeStatusModel[] | null, updatedAt?: number) => void;
  updateRunStatus: (
    runId: string,
    status: RunStatus,
    updates?: Partial<Pick<RunModel, "startedAt" | "finishedAt" | "error">>,
    occurredAt?: number,
  ) => void;
  updateRunNode: (
    runId: string,
    nodeId: string,
    mutator: (node: RunNodeStatusModel) => RunNodeStatusModel,
  ) => void;
  applyNodeResultDelta: (runId: string, nodeId: string, delta: NodeResultDeltaModel) => void;
};

const DEFAULT_RUN_STALE_MS = 30_000;
const DEFAULT_LIST_STALE_MS = 30_000;
const DEFAULT_DEFINITION_STALE_MS = 120_000;

const buildParamsKey = (params?: RunsQueryParams): { key: string; normalized: RunsQueryParamsNormalized } => {
  const normalized: RunsQueryParamsNormalized = {
    limit: params?.limit ?? null,
    cursor: params?.cursor ?? null,
    status: params?.status ?? null,
    clientId: params?.clientId ?? null,
  };
  const key = buildKey(normalized.limit, normalized.cursor, normalized.status, normalized.clientId);
  return { key, normalized };
};

const initialMeta = (staleAfter: number): RunMeta => ({
  status: "idle",
  error: null,
  staleAfter,
});

export const useRunsStore = create<RunsState>()(
  immer((set, get) => ({
    byId: {},
    metaById: {},
    lists: {},
    definitions: {},

    fetchRuns: async (params, options) => {
      const { key, normalized } = buildParamsKey(params);
      const now = Date.now();
      const currentList = get().lists[key];
      const staleAfter = options?.staleAfter ?? currentList?.staleAfter ?? DEFAULT_LIST_STALE_MS;

      if (currentList?.status === "success" && isCacheFresh(currentList.updatedAt, staleAfter, now, options?.force)) {
        return currentList.ids
          .map((id) => get().byId[id])
          .filter((run): run is RunModel => Boolean(run));
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
        const payload = await runsGateway.list(params, { dedupeKey: `runs:${key}` });
        const items = payload.items;
        set((state) => {
          const metaById = state.metaById;
          items.forEach((run) => {
            state.byId[run.runId] = run;
            const existingMeta = metaById[run.runId];
            metaById[run.runId] = {
              ...(existingMeta ?? initialMeta(DEFAULT_RUN_STALE_MS)),
              status: "success",
              error: null,
              updatedAt: now,
            };
          });

          const next = state.lists[key]!;
          next.ids = items.map((run) => run.runId);
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

    getRun: async (runId, options) => {
      if (!runId) {
        return null;
      }
      const now = Date.now();
      const existingRun = get().byId[runId];
      const existingMeta = get().metaById[runId];
      const staleAfter = options?.staleAfter ?? existingMeta?.staleAfter ?? DEFAULT_RUN_STALE_MS;
      if (
        existingRun &&
        existingMeta?.status === "success" &&
        isCacheFresh(existingMeta.updatedAt, staleAfter, now, options?.force)
      ) {
        return existingRun;
      }

      set((state) => {
        state.metaById[runId] = {
          ...(state.metaById[runId] ?? initialMeta(staleAfter)),
          status: "loading",
          error: null,
          staleAfter,
        };
      });

      try {
        const run = await runsGateway.get(runId, { dedupeKey: `run:${runId}` });
        set((state) => {
          state.byId[runId] = run;
          state.metaById[runId] = {
            ...(state.metaById[runId] ?? initialMeta(staleAfter)),
            status: "success",
            error: null,
            updatedAt: now,
            staleAfter,
          };
        });
        return run;
      } catch (error) {
        const apiError = toApiError(error);
        set((state) => {
          state.metaById[runId] = {
            ...(state.metaById[runId] ?? initialMeta(staleAfter)),
            status: "error",
            error: apiError,
            updatedAt: now,
            staleAfter,
          };
        });
        throw apiError;
      }
    },

    getRunDefinition: async (runId, options) => {
      if (!runId) {
        return null;
      }
      const now = Date.now();
      const current = get().definitions[runId];
      const staleAfter =
        options?.staleAfter ?? current?.staleAfter ?? DEFAULT_DEFINITION_STALE_MS;
      if (
        current?.status === "success" &&
        isCacheFresh(current.updatedAt, staleAfter, now, options?.force)
      ) {
        return current.data ?? null;
      }

      set((state) => {
        state.definitions[runId] = {
          ...(state.definitions[runId] ?? {
            runId,
            data: null,
            status: "idle",
            error: null,
            staleAfter,
          }),
          status: "loading",
          error: null,
          staleAfter,
        };
      });

      try {
        const definition = await runsGateway.getDefinition(runId);
        set((state) => {
          state.definitions[runId] = {
            runId,
            data: definition,
            status: "success",
            error: null,
            updatedAt: now,
            staleAfter,
          };
        });
        return definition;
      } catch (error) {
        const apiError = toApiError(error);
        set((state) => {
          state.definitions[runId] = {
            ...(state.definitions[runId] ?? {
              runId,
              data: null,
              status: "idle",
              error: null,
              staleAfter,
            }),
            status: "error",
            error: apiError,
            updatedAt: now,
            staleAfter,
          };
        });
        throw apiError;
      }
    },

    startRun: async (payload, options) => {
      const run = await runsGateway.start(payload, options);
      const now = Date.now();
      set((state) => {
        state.byId[run.runId] = run;
        state.metaById[run.runId] = {
          ...(state.metaById[run.runId] ?? initialMeta(DEFAULT_RUN_STALE_MS)),
          status: "success",
          error: null,
          updatedAt: now,
        };
      });
      return run;
    },

    cancelRun: async (runId) => {
      await runsGateway.cancel(runId);
      set((state) => {
        const run = state.byId[runId];
        if (run) {
          state.byId[runId] = { ...run, status: "cancelled" };
          const meta = state.metaById[runId] ?? initialMeta(DEFAULT_RUN_STALE_MS);
          state.metaById[runId] = { ...meta, status: "success", error: null, updatedAt: Date.now() };
        }
      });
    },

    upsertRun: (run, updatedAt) => {
      const timestamp = updatedAt ?? Date.now();
      set((state) => {
        const existing = state.byId[run.runId];
        const merged = normalizeRun({
          ...(existing ?? {}),
          ...run,
          runId: run.runId,
        } as RunModel);
        state.byId[run.runId] = merged;
        state.metaById[run.runId] = {
          ...(state.metaById[run.runId] ?? initialMeta(DEFAULT_RUN_STALE_MS)),
          status: "success",
          error: null,
          updatedAt: timestamp,
        };
      });
    },

    mergeRunSnapshot: (run, nodes, updatedAt) => {
      const timestamp = updatedAt ?? Date.now();
      set((state) => {
        const existing = state.byId[run.runId];
        const nextNodes = nodes ?? run.nodes ?? existing?.nodes ?? [];
        const merged = normalizeRun({
          ...(existing ?? {}),
          ...run,
          runId: run.runId,
          nodes: nextNodes,
        } as RunModel);
        state.byId[run.runId] = merged;
        state.metaById[run.runId] = {
          ...(state.metaById[run.runId] ?? initialMeta(DEFAULT_RUN_STALE_MS)),
          status: "success",
          error: null,
          updatedAt: timestamp,
        };
      });
    },

    updateRunStatus: (runId, status, updates, occurredAt) => {
      const nextTimestamp = occurredAt ?? Date.now();
      set((state) => {
        const existing = state.byId[runId];
        if (!existing) {
          state.byId[runId] = normalizeRun({
            runId,
            status,
            definitionHash: "",
            clientId: "",
            startedAt: updates?.startedAt ?? null,
            finishedAt: updates?.finishedAt ?? null,
            nodes: [],
          } as RunModel);
        } else {
          state.byId[runId] = {
            ...existing,
            status,
            ...updates,
          };
        }
        state.metaById[runId] = {
          ...(state.metaById[runId] ?? initialMeta(DEFAULT_RUN_STALE_MS)),
          status: "success",
          error: null,
          updatedAt: nextTimestamp,
        };
      });
    },

    updateRunNode: (runId, nodeId, mutator) => {
      set((state) => {
        const run = state.byId[runId];
        if (!run?.nodes?.length) {
          return;
        }
        const index = run.nodes.findIndex((node) => node.nodeId === nodeId);
        if (index === -1) {
          return;
        }
        const currentNode = run.nodes[index];
        const nextNode = mutator(currentNode);
        if (nextNode === currentNode) {
          return;
        }
        const nextNodes = run.nodes.slice();
        nextNodes[index] = nextNode;
        state.byId[runId] = { ...run, nodes: nextNodes };
        state.metaById[runId] = {
          ...(state.metaById[runId] ?? initialMeta(DEFAULT_RUN_STALE_MS)),
          status: "success",
          error: null,
          updatedAt: Date.now(),
        };
      });
    },

    applyNodeResultDelta: (runId, nodeId, delta) => {
      set((state) => {
        const run = state.byId[runId];
        if (!run?.nodes?.length) {
          return;
        }
        let changed = false;
        const nextNodes = run.nodes.map((node) => {
          if (node.nodeId === nodeId) {
            const current = (node.result as Record<string, unknown> | null | undefined) ?? {};
            const result = applyResultDelta(current, delta);
            if (!result.changed) {
              return node;
            }
            changed = true;
            return { ...node, result: result.next ?? {} };
          }
          const middlewares = (node as { middlewares?: { id?: string; result?: unknown }[] }).middlewares;
          if (!middlewares?.length) {
            return node;
          }
          let mwChanged = false;
          const nextMiddlewares = middlewares.map((mw) => {
            if (mw.id !== nodeId) {
              return mw;
            }
            const current = (mw.result as Record<string, unknown> | null | undefined) ?? {};
            const result = applyResultDelta(current, delta);
            if (!result.changed) {
              return mw;
            }
            mwChanged = true;
            return { ...mw, result: result.next ?? {} };
          });
          if (!mwChanged) {
            return node;
          }
          changed = true;
          return { ...node, middlewares: nextMiddlewares };
        });
        if (!changed) {
          return;
        }
        state.byId[runId] = { ...run, nodes: nextNodes };
        state.metaById[runId] = {
          ...(state.metaById[runId] ?? initialMeta(DEFAULT_RUN_STALE_MS)),
          status: "success",
          error: null,
          updatedAt: Date.now(),
        };
      });
    },
  })),
);

export const useRuns = (params?: RunsQueryParams, options?: { enabled?: boolean }) => {
  const enabled = options?.enabled ?? true;
  const { key } = useMemo(() => buildParamsKey(params), [params?.limit, params?.cursor, params?.status, params?.clientId]);
  const list = useRunsStore((state) => state.lists[key]);
  const byId = useRunsStore((state) => state.byId);
  const fetchRuns = useRunsStore((state) => state.fetchRuns);

  useEffect(() => {
    if (enabled) {
      fetchRuns(params);
    }
  }, [enabled, fetchRuns, key]);

  const items = useMemo(
    () => list?.ids.map((id) => byId[id]).filter((run): run is RunModel => Boolean(run)) ?? [],
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
    () => (enabled ? fetchRuns(params, { force: true }) : Promise.resolve([])),
    [enabled, fetchRuns, key],
  );

  return {
    ...selected,
    isLoading: selected.status === "loading",
    isError: selected.status === "error",
    refetch,
  };
};

export const useRun = (runId?: string) => {
  const run = useRunsStore((state) => (runId ? state.byId[runId] : undefined));
  const meta = useRunsStore((state) => (runId ? state.metaById[runId] : undefined));
  const getRun = useRunsStore((state) => state.getRun);

  useEffect(() => {
    if (runId) {
      void getRun(runId);
    }
  }, [getRun, runId]);

  const selected = useMemo(
    () => ({
      run: run ?? null,
      status: meta?.status ?? ("idle" as ResourceStatus),
      error: meta?.error ?? null,
    }),
    [meta?.error, meta?.status, run],
  );

  const refetch = useCallback(
    () => (runId ? getRun(runId, { force: true }) : Promise.resolve(null)),
    [getRun, runId],
  );

  return {
    ...selected,
    isLoading: selected.status === "loading",
    isError: selected.status === "error",
    refetch,
  };
};

export const useRunDefinition = (runId?: string) => {
  const entry = useRunsStore((state) => (runId ? state.definitions[runId] : undefined));
  const getRunDefinition = useRunsStore((state) => state.getRunDefinition);

  useEffect(() => {
    if (runId) {
      void getRunDefinition(runId);
    }
  }, [getRunDefinition, runId]);

  const selected = useMemo(
    () => ({
      definition: entry?.data ?? null,
      status: entry?.status ?? ("idle" as ResourceStatus),
      error: entry?.error ?? null,
    }),
    [entry?.data, entry?.error, entry?.status],
  );

  const refetch = useCallback(
    () => (runId ? getRunDefinition(runId, { force: true }) : Promise.resolve(null)),
    [getRunDefinition, runId],
  );

  return {
    ...selected,
    isLoading: selected.status === "loading",
    isError: selected.status === "error",
    refetch,
  };
};
