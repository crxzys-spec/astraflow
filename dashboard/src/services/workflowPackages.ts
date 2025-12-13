import { WorkflowPackagesApi } from "../client/apis/workflow-packages-api";
import type {
  WorkflowPackageCloneRequest,
  WorkflowPackageList,
  WorkflowPackageSummary,
  WorkflowPublishRequest,
  WorkflowPublishResponse,
  WorkflowRef,
} from "../client/models";
import { createApi } from "../api/client";
import { apiRequest } from "../api/fetcher";
import { toListModel } from "../lib/normalize";

const workflowPackagesApi = createApi(WorkflowPackagesApi);

export type WorkflowPackagesQueryParams = {
  limit?: number;
  cursor?: string;
  owner?: string;
  visibility?: string;
  search?: string;
};

export type WorkflowPackageSummaryModel = WorkflowPackageSummary & {
  id: string;
  displayName: string;
  latestVersion?: WorkflowPackageSummary["latestVersion"];
  previewImage?: string | null;
};

export type WorkflowPackageListModel = {
  items: WorkflowPackageSummaryModel[];
  nextCursor: string | null;
};

const normalizeWorkflowPackage = (
  pkg: WorkflowPackageSummary | WorkflowPackageSummaryModel,
): WorkflowPackageSummaryModel => ({
  ...pkg,
  id: pkg.id ?? "",
  displayName: pkg.displayName ?? pkg.slug ?? pkg.id ?? "",
  previewImage: pkg.previewImage ?? pkg.latestVersion?.previewImage ?? null,
  latestVersion: pkg.latestVersion ?? undefined,
});

const fromApiWorkflowPackageList = (payload: WorkflowPackageList): WorkflowPackageListModel =>
  toListModel(payload, normalizeWorkflowPackage);

export const listWorkflowPackages = async (
  params?: WorkflowPackagesQueryParams,
): Promise<WorkflowPackageListModel> => {
  const response = await apiRequest(() =>
    workflowPackagesApi.listWorkflowPackages(
      params?.limit,
      params?.cursor,
      params?.owner,
      params?.visibility,
      params?.search,
    ),
  );
  return fromApiWorkflowPackageList(response.data as WorkflowPackageList);
};

export const publishWorkflow = async (
  workflowId: string,
  data: WorkflowPublishRequest,
): Promise<WorkflowPublishResponse> => {
  const response = await apiRequest(() => workflowPackagesApi.publishWorkflow(workflowId, data));
  return response.data;
};

export const cloneWorkflowPackage = async (
  packageId: string,
  data?: WorkflowPackageCloneRequest,
): Promise<WorkflowRef> => {
  const response = await apiRequest(() => workflowPackagesApi.cloneWorkflowPackage(packageId, data));
  return response.data;
};

export const deleteWorkflowPackage = async (packageId: string): Promise<void> => {
  await apiRequest(() => workflowPackagesApi.deleteWorkflowPackage(packageId));
};

export const workflowPackagesGateway = {
  list: listWorkflowPackages,
  publish: publishWorkflow,
  clone: cloneWorkflowPackage,
  delete: deleteWorkflowPackage,
};
