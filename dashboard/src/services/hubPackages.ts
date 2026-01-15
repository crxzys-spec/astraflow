import { HubPackagesApi } from "../client/apis/hub-packages-api";
import type {
  HubPackageInstallRequest,
  HubPackageInstallResponse,
  HubPackageListResponse,
  HubPackageSummary,
  HubPackageVersionDetail,
  HubVisibility,
} from "../client/models";
import { apiAxios, createApi } from "../api/client";
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

export type HubPackagePublishPayload = {
  file: File;
  visibility?: HubVisibility;
  summary?: string;
  readme?: string;
  tags?: string[];
};

export type HubLocalPackagePublishPayload = {
  name: string;
  version?: string;
  visibility?: HubVisibility;
  summary?: string;
  readme?: string;
  tags?: string[];
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
  owner: string,
  name: string,
  data?: HubPackageInstallRequest,
): Promise<HubPackageInstallResponse> => {
  const response = await apiRequest(() => hubPackagesApi.installHubPackage(owner, name, data));
  return response.data as HubPackageInstallResponse;
};

export const uninstallHubPackage = async (
  owner: string,
  name: string,
  data?: HubPackageInstallRequest,
): Promise<HubPackageInstallResponse> => {
  const response = await apiRequest(() => hubPackagesApi.uninstallHubPackage(owner, name, data));
  return response.data as HubPackageInstallResponse;
};

export const publishHubPackage = async (
  payload: HubPackagePublishPayload,
): Promise<HubPackageVersionDetail> => {
  const response = await apiRequest(() =>
    hubPackagesApi.publishHubPackage(
      payload.file,
      payload.visibility,
      payload.summary,
      payload.readme,
      payload.tags,
    ),
  );
  return response.data as HubPackageVersionDetail;
};

export const publishHubPackageLocal = async (
  payload: HubLocalPackagePublishPayload,
): Promise<HubPackageVersionDetail> => {
  const response = await apiRequest(() => apiAxios.post("/api/v1/hub/packages/local", payload));
  return response.data as HubPackageVersionDetail;
};

export const hubPackagesGateway = {
  list: listHubPackages,
  install: installHubPackage,
  uninstall: uninstallHubPackage,
  publish: publishHubPackageLocal,
};
