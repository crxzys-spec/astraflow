import { useCallback, useEffect, useMemo } from "react";
import { create } from "zustand";
import { immer } from "zustand/middleware/immer";
import { toApiError, type ApiError } from "../api/fetcher";
import type {
  WorkflowPackageCloneRequest,
  WorkflowPublishRequest,
  WorkflowPublishResponse,
  WorkflowRef,
} from "../client/models";
import type { WorkflowPackageSummaryModel, WorkflowPackagesQueryParams } from "../services/workflowPackages";
import { workflowPackagesGateway } from "../services/workflowPackages";
import { buildKey, isCacheFresh, type ResourceStatus } from "./shared";

type WorkflowPackagesQueryParamsNormalized = {
  limit: number | null;
  cursor: string | null;
  owner: string | null;
  visibility: string | null;
  search: string | null;
};

type PackageListState = {
  key: string;
  params: WorkflowPackagesQueryParamsNormalized;
  ids: string[];
  nextCursor?: string | null;
  status: ResourceStatus;
  error: ApiError | null;
  updatedAt?: number;
  staleAfter: number;
};

type WorkflowPackagesState = {
  byId: Record<string, WorkflowPackageSummaryModel>;
  lists: Record<string, PackageListState>;
  fetchPackages: (
    params?: WorkflowPackagesQueryParams,
    options?: { force?: boolean; staleAfter?: number },
  ) => Promise<WorkflowPackageSummaryModel[]>;
  clonePackage: (
    packageId: string,
    data?: WorkflowPackageCloneRequest,
  ) => Promise<WorkflowRef>;
  deletePackage: (packageId: string) => Promise<void>;
  publishWorkflow: (workflowId: string, data: WorkflowPublishRequest) => Promise<WorkflowPublishResponse>;
};

const DEFAULT_LIST_STALE_MS = 30_000;

const buildParamsKey = (
  params?: WorkflowPackagesQueryParams,
): { key: string; normalized: WorkflowPackagesQueryParamsNormalized } => {
  const normalized: WorkflowPackagesQueryParamsNormalized = {
    limit: params?.limit ?? null,
    cursor: params?.cursor ?? null,
    owner: params?.owner ?? null,
    visibility: params?.visibility ?? null,
    search: params?.search ?? null,
  };
  const key = buildKey(
    normalized.limit,
    normalized.cursor,
    normalized.owner,
    normalized.visibility,
    normalized.search,
  );
  return { key, normalized };
};

export const useWorkflowPackagesStore = create<WorkflowPackagesState>()(
  immer((set, get) => ({
    byId: {},
    lists: {},

    fetchPackages: async (params, options) => {
      const { key, normalized } = buildParamsKey(params);
      const now = Date.now();
      const currentList = get().lists[key];
      const staleAfter = options?.staleAfter ?? currentList?.staleAfter ?? DEFAULT_LIST_STALE_MS;

      if (currentList?.status === "success" && isCacheFresh(currentList.updatedAt, staleAfter, now, options?.force)) {
        return currentList.ids
          .map((id) => get().byId[id])
          .filter((pkg): pkg is WorkflowPackageSummaryModel => Boolean(pkg));
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
        const payload = await workflowPackagesGateway.list(params);
        const items = payload.items;
        set((state) => {
          items.forEach((pkg) => {
            state.byId[pkg.id] = pkg;
          });
          const next = state.lists[key]!;
          next.ids = items.map((pkg) => pkg.id);
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

    clonePackage: async (packageId, data) => workflowPackagesGateway.clone(packageId, data),

    deletePackage: async (packageId) => {
      await workflowPackagesGateway.delete(packageId);
      set((state) => {
        delete state.byId[packageId];
        Object.values(state.lists).forEach((list) => {
          list.ids = list.ids.filter((id) => id !== packageId);
        });
      });
    },

    publishWorkflow: async (workflowId, data) => workflowPackagesGateway.publish(workflowId, data),
  })),
);

export const useWorkflowPackages = (
  params?: WorkflowPackagesQueryParams,
  options?: { enabled?: boolean },
) => {
  const enabled = options?.enabled ?? true;
  const { key } = useMemo(() => buildParamsKey(params), [params?.limit, params?.cursor, params?.owner, params?.visibility, params?.search]);
  const list = useWorkflowPackagesStore((state) => state.lists[key]);
  const byId = useWorkflowPackagesStore((state) => state.byId);
  const fetchList = useWorkflowPackagesStore((state) => state.fetchPackages);

  useEffect(() => {
    if (enabled) {
      fetchList(params);
    }
  }, [enabled, fetchList, key]);

  const items = useMemo(
    () => list?.ids.map((id) => byId[id]).filter((pkg): pkg is WorkflowPackageSummaryModel => Boolean(pkg)) ?? [],
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
