import { useCallback, useEffect, useMemo } from "react";
import { create } from "zustand";
import { immer } from "zustand/middleware/immer";
import { toApiError, type ApiError } from "../api/fetcher";
import type { HubWorkflowSummaryModel, HubWorkflowsQueryParams } from "../services/hubWorkflows";
import { hubWorkflowsGateway } from "../services/hubWorkflows";
import { buildKey, isCacheFresh, type ResourceStatus } from "./shared";

type HubWorkflowsQueryParamsNormalized = {
  owner: string | null;
  search: string | null;
  tag: string | null;
  page: number;
  pageSize: number;
};

type HubWorkflowListState = {
  key: string;
  params: HubWorkflowsQueryParamsNormalized;
  ids: string[];
  status: ResourceStatus;
  error: ApiError | null;
  updatedAt?: number;
  staleAfter: number;
};

type HubWorkflowsState = {
  byId: Record<string, HubWorkflowSummaryModel>;
  lists: Record<string, HubWorkflowListState>;
  fetchWorkflows: (
    params?: HubWorkflowsQueryParams,
    options?: { force?: boolean; staleAfter?: number },
  ) => Promise<HubWorkflowSummaryModel[]>;
};

const DEFAULT_LIST_STALE_MS = 30_000;

const buildParamsKey = (
  params?: HubWorkflowsQueryParams,
): { key: string; normalized: HubWorkflowsQueryParamsNormalized } => {
  const normalized: HubWorkflowsQueryParamsNormalized = {
    owner: params?.owner ?? null,
    search: params?.search ?? null,
    tag: params?.tag ?? null,
    page: params?.page ?? 1,
    pageSize: params?.pageSize ?? 48,
  };
  const key = buildKey(
    normalized.owner,
    normalized.search,
    normalized.tag,
    normalized.page,
    normalized.pageSize,
  );
  return { key, normalized };
};

export const useHubWorkflowsStore = create<HubWorkflowsState>()(
  immer((set, get) => ({
    byId: {},
    lists: {},

    fetchWorkflows: async (params, options) => {
      const { key, normalized } = buildParamsKey(params);
      const now = Date.now();
      const currentList = get().lists[key];
      const staleAfter = options?.staleAfter ?? currentList?.staleAfter ?? DEFAULT_LIST_STALE_MS;

      if (
        currentList?.status === "success" &&
        isCacheFresh(currentList.updatedAt, staleAfter, now, options?.force)
      ) {
        return currentList.ids
          .map((id) => get().byId[id])
          .filter((workflow): workflow is HubWorkflowSummaryModel => Boolean(workflow));
      }

      set((state) => {
        const next = state.lists[key] ?? {
          key,
          params: normalized,
          ids: [],
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
        const payload = await hubWorkflowsGateway.list(params);
        const items = payload.items;
        set((state) => {
          items.forEach((workflow) => {
            state.byId[workflow.id] = workflow;
          });
          const next = state.lists[key]!;
          next.ids = items.map((workflow) => workflow.id);
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
  })),
);

export const useHubWorkflows = (
  params?: HubWorkflowsQueryParams,
  options?: { enabled?: boolean },
) => {
  const enabled = options?.enabled ?? true;
  const { key } = useMemo(
    () => buildParamsKey(params),
    [params?.owner, params?.search, params?.tag, params?.page, params?.pageSize],
  );
  const list = useHubWorkflowsStore((state) => state.lists[key]);
  const byId = useHubWorkflowsStore((state) => state.byId);
  const fetchList = useHubWorkflowsStore((state) => state.fetchWorkflows);

  useEffect(() => {
    if (enabled) {
      fetchList(params);
    }
  }, [enabled, fetchList, key]);

  const items = useMemo(
    () =>
      list?.ids
        .map((id) => byId[id])
        .filter((workflow): workflow is HubWorkflowSummaryModel => Boolean(workflow)) ?? [],
    [byId, list?.ids],
  );
  const selected = useMemo(
    () => ({
      items,
      status: list?.status ?? ("idle" as ResourceStatus),
      error: list?.error ?? null,
    }),
    [items, list?.error, list?.status],
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
