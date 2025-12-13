import { useCallback, useEffect, useMemo } from "react";
import { create } from "zustand";
import { immer } from "zustand/middleware/immer";
import { toApiError, type ApiError } from "../api/fetcher";
import type { WorkflowModel, WorkflowsQueryParams } from "../services/workflows";
import { workflowsGateway } from "../services/workflows";
import { buildKey, isCacheFresh, type ResourceStatus } from "./shared";

type WorkflowsQueryParamsNormalized = {
  limit: number | null;
  cursor: string | null;
};

type WorkflowMeta = {
  status: ResourceStatus;
  error: ApiError | null;
  updatedAt?: number;
  staleAfter: number;
};

type WorkflowListState = {
  key: string;
  params: WorkflowsQueryParamsNormalized;
  ids: string[];
  nextCursor?: string | null;
  status: ResourceStatus;
  error: ApiError | null;
  updatedAt?: number;
  staleAfter: number;
};

type WorkflowsState = {
  byId: Record<string, WorkflowModel>;
  metaById: Record<string, WorkflowMeta>;
  lists: Record<string, WorkflowListState>;
  fetchWorkflows: (
    params?: WorkflowsQueryParams,
    options?: { force?: boolean; staleAfter?: number },
  ) => Promise<WorkflowModel[]>;
  getWorkflow: (
    workflowId: string,
    options?: { force?: boolean; staleAfter?: number },
  ) => Promise<WorkflowModel | null>;
  deleteWorkflow: (workflowId: string) => Promise<void>;
};

const DEFAULT_LIST_STALE_MS = 30_000;
const DEFAULT_WORKFLOW_STALE_MS = 60_000;

const buildParamsKey = (params?: WorkflowsQueryParams): { key: string; normalized: WorkflowsQueryParamsNormalized } => {
  const normalized: WorkflowsQueryParamsNormalized = {
    limit: params?.limit ?? null,
    cursor: params?.cursor ?? null,
  };
  const key = buildKey(normalized.limit, normalized.cursor);
  return { key, normalized };
};

export const useWorkflowsStore = create<WorkflowsState>()(
  immer((set, get) => ({
    byId: {},
    metaById: {},
    lists: {},

    fetchWorkflows: async (params, options) => {
      const { key, normalized } = buildParamsKey(params);
      const now = Date.now();
      const currentList = get().lists[key];
      const staleAfter = options?.staleAfter ?? currentList?.staleAfter ?? DEFAULT_LIST_STALE_MS;

      if (currentList?.status === "success" && isCacheFresh(currentList.updatedAt, staleAfter, now, options?.force)) {
        return currentList.ids
          .map((id) => get().byId[id])
          .filter((workflow): workflow is WorkflowModel => Boolean(workflow));
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
        const payload = await workflowsGateway.list(params, { dedupeKey: `workflows:${key}` });
        const items = payload.items;
        set((state) => {
          items.forEach((workflow) => {
            state.byId[workflow.id] = workflow;
          });
          const next = state.lists[key]!;
          next.ids = items.map((workflow) => workflow.id);
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

    deleteWorkflow: async (workflowId) => {
      await workflowsGateway.delete(workflowId);
      set((state) => {
        delete state.byId[workflowId];
        delete state.metaById[workflowId];
        Object.values(state.lists).forEach((list) => {
          list.ids = list.ids.filter((id) => id !== workflowId);
        });
      });
    },

    getWorkflow: async (workflowId, options) => {
      if (!workflowId) {
        return null;
      }
      const now = Date.now();
      const existing = get().byId[workflowId];
      const existingMeta = get().metaById[workflowId];
      const staleAfter = options?.staleAfter ?? existingMeta?.staleAfter ?? DEFAULT_WORKFLOW_STALE_MS;
      if (
        existing &&
        existingMeta?.status === "success" &&
        isCacheFresh(existingMeta.updatedAt, staleAfter, now, options?.force)
      ) {
        return existing;
      }

      set((state) => {
        state.metaById[workflowId] = {
          ...(state.metaById[workflowId] ?? {
            status: "idle" as ResourceStatus,
            error: null,
            staleAfter,
          }),
          status: "loading",
          error: null,
          staleAfter,
        };
      });

      try {
        const workflow = await workflowsGateway.get(workflowId, { dedupeKey: `workflow:${workflowId}` });
        set((state) => {
          state.byId[workflowId] = workflow;
          state.metaById[workflowId] = {
            ...(state.metaById[workflowId] ?? {
              status: "idle" as ResourceStatus,
              error: null,
              staleAfter,
            }),
            status: "success",
            error: null,
            updatedAt: now,
            staleAfter,
          };
        });
        return workflow;
      } catch (error) {
        const apiError = toApiError(error);
        set((state) => {
          state.metaById[workflowId] = {
            ...(state.metaById[workflowId] ?? {
              status: "idle" as ResourceStatus,
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
  })),
);

export const useWorkflows = (params?: WorkflowsQueryParams, options?: { enabled?: boolean }) => {
  const enabled = options?.enabled ?? true;
  const { key } = useMemo(() => buildParamsKey(params), [params?.limit, params?.cursor]);
  const list = useWorkflowsStore((state) => state.lists[key]);
  const byId = useWorkflowsStore((state) => state.byId);
  const fetchList = useWorkflowsStore((state) => state.fetchWorkflows);

  useEffect(() => {
    if (enabled) {
      fetchList(params);
    }
  }, [enabled, fetchList, key]);

  const items = useMemo(
    () => list?.ids.map((id) => byId[id]).filter((workflow): workflow is WorkflowModel => Boolean(workflow)) ?? [],
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

export const useWorkflow = (workflowId?: string) => {
  const workflow = useWorkflowsStore((state) => (workflowId ? state.byId[workflowId] : undefined));
  const meta = useWorkflowsStore((state) => (workflowId ? state.metaById[workflowId] : undefined));
  const getWorkflow = useWorkflowsStore((state) => state.getWorkflow);

  useEffect(() => {
    if (workflowId) {
      void getWorkflow(workflowId);
    }
  }, [getWorkflow, workflowId]);

  const selected = useMemo(
    () => ({
      workflow: workflow ?? null,
      status: meta?.status ?? ("idle" as ResourceStatus),
      error: meta?.error ?? null,
      updatedAt: meta?.updatedAt ?? 0,
    }),
    [meta?.error, meta?.status, meta?.updatedAt, workflow],
  );

  const refetch = useCallback(
    () => (workflowId ? getWorkflow(workflowId, { force: true }) : Promise.resolve(null)),
    [getWorkflow, workflowId],
  );

  return {
    ...selected,
    isLoading: selected.status === "loading",
    isError: selected.status === "error",
    refetch,
  };
};
