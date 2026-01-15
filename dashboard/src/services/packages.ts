import { PackagesApi } from "../client/apis/packages-api";
import { apiAxios, createApi } from "../api/client";
import { apiRequest } from "../api/fetcher";
import type { PackageDetail, PackageSummary } from "../client/models";

const packagesApi = createApi(PackagesApi);

const splitPackageRef = (packageName: string): { owner: string; name: string } | null => {
  const parts = packageName.split("/");
  if (parts.length < 2) {
    return null;
  }
  const [owner, ...rest] = parts;
  const name = rest.join("/").trim();
  if (!owner || !name) {
    return null;
  }
  return { owner, name };
};

export const getPackage = async (packageName: string, version?: string): Promise<PackageDetail> => {
  const ownerRef = splitPackageRef(packageName);
  if (ownerRef) {
    const response = await apiRequest((config) =>
      apiAxios.get<PackageDetail>(`/api/v1/packages/${ownerRef.owner}/${ownerRef.name}`, {
        ...config,
        params: version ? { version } : undefined,
      }),
    );
    return response.data;
  }
  const response = await apiRequest(() => packagesApi.getPackage(packageName, version));
  return response.data;
};

export const listPackages = async (): Promise<PackageSummary[]> => {
  const response = await apiRequest((config) => packagesApi.listPackages(config));
  return response.data.items ?? [];
};
