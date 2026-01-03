import { useCallback, useEffect, useMemo } from "react";
import { create } from "zustand";
import { immer } from "zustand/middleware/immer";
import { toApiError, type ApiError } from "../api/fetcher";
import type { HubPackageSummaryModel, HubPackagesQueryParams } from "../services/hubPackages";
import { hubPackagesGateway } from "../services/hubPackages";
import { buildKey, isCacheFresh, type ResourceStatus } from "./shared";

type HubPackagesQueryParamsNormalized = {
  owner: string | null;
  search: string | null;
  tag: string | null;
  page: number;
  pageSize: number;
};

type HubPackageListState = {
  key: string;
  params: HubPackagesQueryParamsNormalized;
  names: string[];
  status: ResourceStatus;
  error: ApiError | null;
  updatedAt?: number;
  staleAfter: number;
};

type HubPackagesState = {
  byName: Record<string, HubPackageSummaryModel>;
  lists: Record<string, HubPackageListState>;
  fetchPackages: (
    params?: HubPackagesQueryParams,
    options?: { force?: boolean; staleAfter?: number },
  ) => Promise<HubPackageSummaryModel[]>;
};

const DEFAULT_LIST_STALE_MS = 30_000;

const buildParamsKey = (
  params?: HubPackagesQueryParams,
): { key: string; normalized: HubPackagesQueryParamsNormalized } => {
  const normalized: HubPackagesQueryParamsNormalized = {
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

export const useHubPackagesStore = create<HubPackagesState>()(
  immer((set, get) => ({
    byName: {},
    lists: {},

    fetchPackages: async (params, options) => {
      const { key, normalized } = buildParamsKey(params);
      const now = Date.now();
      const currentList = get().lists[key];
      const staleAfter = options?.staleAfter ?? currentList?.staleAfter ?? DEFAULT_LIST_STALE_MS;

      if (
        currentList?.status === "success" &&
        isCacheFresh(currentList.updatedAt, staleAfter, now, options?.force)
      ) {
        return currentList.names
          .map((name) => get().byName[name])
          .filter((pkg): pkg is HubPackageSummaryModel => Boolean(pkg));
      }

      set((state) => {
        const next = state.lists[key] ?? {
          key,
          params: normalized,
          names: [],
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
        const payload = await hubPackagesGateway.list(params);
        const items = payload.items;
        set((state) => {
          items.forEach((pkg) => {
            state.byName[pkg.name] = pkg;
          });
          const next = state.lists[key]!;
          next.names = items.map((pkg) => pkg.name);
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

export const useHubPackages = (
  params?: HubPackagesQueryParams,
  options?: { enabled?: boolean },
) => {
  const enabled = options?.enabled ?? true;
  const { key } = useMemo(
    () => buildParamsKey(params),
    [params?.owner, params?.search, params?.tag, params?.page, params?.pageSize],
  );
  const list = useHubPackagesStore((state) => state.lists[key]);
  const byName = useHubPackagesStore((state) => state.byName);
  const fetchList = useHubPackagesStore((state) => state.fetchPackages);

  useEffect(() => {
    if (enabled) {
      fetchList(params);
    }
  }, [enabled, fetchList, key]);

  const items = useMemo(
    () =>
      list?.names
        .map((name) => byName[name])
        .filter((pkg): pkg is HubPackageSummaryModel => Boolean(pkg)) ?? [],
    [byName, list?.names],
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
