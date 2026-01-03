import { PackagesApi } from "../client/apis/packages-api";
import { createApi } from "../api/client";
import { apiRequest } from "../api/fetcher";
import type { PackageDetail, PackageSummary } from "../client/models";

const packagesApi = createApi(PackagesApi);

export const getPackage = async (packageName: string, version?: string): Promise<PackageDetail> => {
  const response = await apiRequest(() => packagesApi.getPackage(packageName, version));
  return response.data;
};

export const listPackages = async (): Promise<PackageSummary[]> => {
  const response = await apiRequest((config) => packagesApi.listPackages(config));
  return response.data.items ?? [];
};
