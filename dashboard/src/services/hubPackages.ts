import { HubPackagesApi } from "../client/apis/hub-packages-api";
import type {
  HubPackageInstallRequest,
  HubPackageInstallResponse,
  HubPackageListResponse,
  HubPackageSummary,
} from "../client/models";
import { createApi } from "../api/client";
import { apiRequest } from "../api/fetcher";

const hubPackagesApi = createApi(HubPackagesApi);

export type HubPackagesQueryParams = {
  owner?: string;
  search?: string;
  tag?: string;
  page?: number;
  pageSize?: number;
};

export type HubPackageSummaryModel = HubPackageSummary & {
  name: string;
};

export type HubPackageListModel = {
  items: HubPackageSummaryModel[];
  meta: HubPackageListResponse["meta"] | null;
};

const normalizeHubPackage = (pkg: HubPackageSummary): HubPackageSummaryModel => ({
  ...pkg,
  name: pkg.name ?? "",
});

export const listHubPackages = async (
  params?: HubPackagesQueryParams,
): Promise<HubPackageListModel> => {
  const response = await apiRequest(() =>
    hubPackagesApi.listHubPackages(
      params?.search,
      params?.tag,
      params?.owner,
      params?.page ?? 1,
      params?.pageSize ?? 48,
    ),
  );
  const payload = response.data as HubPackageListResponse;
  return {
    items: (payload.items ?? []).map((item) => normalizeHubPackage(item)),
    meta: payload.meta ?? null,
  };
};

export const installHubPackage = async (
  packageName: string,
  data?: HubPackageInstallRequest,
): Promise<HubPackageInstallResponse> => {
  const response = await apiRequest(() => hubPackagesApi.installHubPackage(packageName, data));
  return response.data as HubPackageInstallResponse;
};

export const hubPackagesGateway = {
  list: listHubPackages,
  install: installHubPackage,
};
