import { CatalogApi } from "../client/apis/catalog-api";
import { createApi } from "../api/client";
import { apiRequest } from "../api/fetcher";
import type { CatalogNodeSearchResponse } from "../client/models";

const catalogApi = createApi(CatalogApi);

export const searchCatalogNodes = async (
  q: string,
  packageName?: string,
  options?: { signal?: AbortSignal },
): Promise<CatalogNodeSearchResponse> => {
  const response = await apiRequest(() => catalogApi.searchCatalogNodes(q || "*", packageName), {
    signal: options?.signal,
  });
  return response.data;
};
