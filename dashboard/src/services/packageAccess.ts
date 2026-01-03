import { createApi } from "../api/client";
import { apiRequest } from "../api/fetcher";
import { PackagePermissionsApi } from "../client/apis/package-permissions-api";
import { PackageVaultApi } from "../client/apis/package-vault-api";
import type {
  PackagePermission,
  PackagePermissionCreateRequest,
  PackagePermissionList,
  PackageVaultItem,
  PackageVaultList,
  PackageVaultUpsertRequest,
} from "../client/models";

const permissionsApi = createApi(PackagePermissionsApi);
const vaultApi = createApi(PackageVaultApi);

export const listPackagePermissions = async (packageName?: string): Promise<PackagePermission[]> => {
  const response = await apiRequest<PackagePermissionList>((config) =>
    permissionsApi.listPackagePermissions(packageName, config),
  );
  return response.data.items ?? [];
};

export const createPackagePermission = async (
  payload: PackagePermissionCreateRequest,
): Promise<PackagePermission> => {
  const response = await apiRequest<PackagePermission>((config) =>
    permissionsApi.createPackagePermission(payload, config),
  );
  return response.data;
};

export const deletePackagePermission = async (permissionId: string): Promise<void> => {
  await apiRequest<void>((config) => permissionsApi.deletePackagePermission(permissionId, config));
};

export const listPackageVault = async (packageName: string): Promise<PackageVaultItem[]> => {
  const response = await apiRequest<PackageVaultList>((config) => vaultApi.listPackageVault(packageName, config));
  return response.data.items ?? [];
};

export const upsertPackageVault = async (payload: PackageVaultUpsertRequest): Promise<PackageVaultItem[]> => {
  const response = await apiRequest<PackageVaultList>((config) =>
    vaultApi.upsertPackageVault(payload, config),
  );
  return response.data.items ?? [];
};

export const deletePackageVaultItem = async (packageName: string, key: string): Promise<void> => {
  await apiRequest<void>((config) => vaultApi.deletePackageVaultItem(packageName, key, config));
};

export const packageAccessGateway = {
  listPermissions: listPackagePermissions,
  createPermission: createPackagePermission,
  deletePermission: deletePackagePermission,
  listVault: listPackageVault,
  upsertVault: upsertPackageVault,
  deleteVaultItem: deletePackageVaultItem,
};
