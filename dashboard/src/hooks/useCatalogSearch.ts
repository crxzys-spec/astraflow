import { useCallback, useEffect, useRef, useState } from "react";
import type { CatalogNodeSearchResponse } from "../client/models";
import { searchCatalogNodes } from "../services/catalog";
import type { ApiError } from "../api/fetcher";
import { toApiError } from "../api/fetcher";

type ResourceStatus = "idle" | "loading" | "success" | "error";

export const useCatalogSearch = (
  params: { q: string; package?: string },
  options?: { enabled?: boolean },
) => {
  const enabled = options?.enabled ?? true;
  const [data, setData] = useState<CatalogNodeSearchResponse | null>(null);
  const [status, setStatus] = useState<ResourceStatus>("idle");
  const [error, setError] = useState<ApiError | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const execute = useCallback(
    async (nextParams: { q: string; package?: string }) => {
      if (!enabled) {
        return null;
      }
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;
      setStatus("loading");
      setError(null);
      try {
        const response = await searchCatalogNodes(nextParams.q, nextParams.package, { signal: controller.signal });
        setData(response);
        setStatus("success");
        return response;
      } catch (err) {
        if ((err as { name?: string }).name === "CanceledError" || (err as { name?: string }).name === "AbortError") {
          return null;
        }
        const apiError = toApiError(err);
        setError(apiError);
        setStatus("error");
        return null;
      }
    },
    [enabled],
  );

  useEffect(() => {
    if (!enabled) {
      return;
    }
    void execute(params);
    return () => {
      abortRef.current?.abort();
    };
  }, [enabled, execute, params.package, params.q]);

  const refetch = useCallback(() => execute(params), [execute, params]);

  return {
    data,
    status,
    error,
    isLoading: status === "loading",
    isError: status === "error",
    refetch,
  };
};
