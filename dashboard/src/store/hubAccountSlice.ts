import { useCallback, useEffect } from "react";
import { create } from "zustand";
import { immer } from "zustand/middleware/immer";
import { toApiError, type ApiError } from "../api/fetcher";
import type { HubAccount } from "../client/models";
import { hubAccountGateway } from "../services/hubAccount";
import { isCacheFresh, type ResourceStatus } from "./shared";

type HubAccountState = {
  account: HubAccount | null;
  status: ResourceStatus;
  error: ApiError | null;
  updatedAt?: number;
  staleAfter: number;
  fetchAccount: (options?: { force?: boolean; staleAfter?: number }) => Promise<HubAccount | null>;
};

const DEFAULT_STALE_MS = 30_000;

export const useHubAccountStore = create<HubAccountState>()(
  immer((set, get) => ({
    account: null,
    status: "idle",
    error: null,
    updatedAt: undefined,
    staleAfter: DEFAULT_STALE_MS,

    fetchAccount: async (options) => {
      const now = Date.now();
      const current = get();
      const staleAfter = options?.staleAfter ?? current.staleAfter ?? DEFAULT_STALE_MS;

      if (
        current.status === "success" &&
        isCacheFresh(current.updatedAt, staleAfter, now, options?.force)
      ) {
        return current.account;
      }

      set((state) => {
        state.status = "loading";
        state.error = null;
        state.staleAfter = staleAfter;
      });

      try {
        const account = await hubAccountGateway.get();
        set((state) => {
          state.account = account;
          state.status = "success";
          state.error = null;
          state.updatedAt = now;
          state.staleAfter = staleAfter;
        });
        return account;
      } catch (error) {
        const apiError = toApiError(error);
        set((state) => {
          state.status = "error";
          state.error = apiError;
          state.updatedAt = now;
        });
        throw apiError;
      }
    },
  })),
);

export const useHubAccount = (options?: { enabled?: boolean }) => {
  const enabled = options?.enabled ?? true;
  const account = useHubAccountStore((state) => state.account);
  const status = useHubAccountStore((state) => state.status);
  const error = useHubAccountStore((state) => state.error);
  const fetchAccount = useHubAccountStore((state) => state.fetchAccount);

  useEffect(() => {
    if (enabled) {
      fetchAccount();
    }
  }, [enabled, fetchAccount]);

  const refetch = useCallback(
    () => (enabled ? fetchAccount({ force: true }) : Promise.resolve(account)),
    [account, enabled, fetchAccount],
  );

  return {
    account,
    status,
    error,
    isLoading: status === "loading",
    isError: status === "error",
    refetch,
  };
};
