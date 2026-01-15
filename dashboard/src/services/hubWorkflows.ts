import { HubWorkflowsApi } from "../client/apis/hub-workflows-api";
import type {
  HubWorkflowImportRequest,
  HubWorkflowImportResponse,
  HubWorkflowListResponse,
  HubWorkflowPublishRequest,
  HubWorkflowPublishResponse,
  HubWorkflowSummary,
  HubVisibility,
} from "../client/models";
import { apiAxios, createApi } from "../api/client";
import { apiRequest } from "../api/fetcher";

const hubWorkflowsApi = createApi(HubWorkflowsApi);

export type HubWorkflowsQueryParams = {
  owner?: string;
  search?: string;
  tag?: string;
  page?: number;
  pageSize?: number;
};

export type HubWorkflowSummaryModel = HubWorkflowSummary & {
  id: string;
  name: string;
  previewImage?: string | null;
};

export type HubWorkflowListModel = {
  items: HubWorkflowSummaryModel[];
  meta: HubWorkflowListResponse["meta"] | null;
};

const normalizeHubWorkflow = (
  workflow: HubWorkflowSummary | HubWorkflowSummaryModel,
): HubWorkflowSummaryModel => ({
  ...workflow,
  id: workflow.id ?? "",
  name: workflow.name ?? workflow.id ?? "",
  previewImage: workflow.previewImage ?? null,
});

export const listHubWorkflows = async (
  params?: HubWorkflowsQueryParams,
): Promise<HubWorkflowListModel> => {
  const response = await apiRequest(() =>
    hubWorkflowsApi.listHubWorkflows(
      params?.search,
      params?.tag,
      params?.owner,
      params?.page ?? 1,
      params?.pageSize ?? 48,
    ),
  );
  const payload = response.data as HubWorkflowListResponse;
  return {
    items: (payload.items ?? []).map((item) => normalizeHubWorkflow(item)),
    meta: payload.meta ?? null,
  };
};

export const importHubWorkflow = async (
  workflowId: string,
  data?: HubWorkflowImportRequest,
): Promise<HubWorkflowImportResponse> => {
  const response = await apiRequest(() => hubWorkflowsApi.importHubWorkflow(workflowId, data));
  return response.data as HubWorkflowImportResponse;
};

export const publishHubWorkflow = async (
  payload: HubWorkflowPublishRequest,
): Promise<HubWorkflowPublishResponse> => {
  const response = await apiRequest(() => hubWorkflowsApi.publishHubWorkflow(payload));
  return response.data as HubWorkflowPublishResponse;
};

export type HubLocalWorkflowPublishPayload = {
  workflowId: string;
  version: string;
  name?: string;
  summary?: string;
  description?: string;
  tags?: string[];
  visibility?: HubVisibility;
};

export const publishHubWorkflowLocal = async (
  payload: HubLocalWorkflowPublishPayload,
): Promise<HubWorkflowPublishResponse> => {
  const response = await apiRequest(() => apiAxios.post("/api/v1/hub/workflows/local", payload));
  return response.data as HubWorkflowPublishResponse;
};

export const hubWorkflowsGateway = {
  list: listHubWorkflows,
  import: importHubWorkflow,
  publish: publishHubWorkflowLocal,
};
