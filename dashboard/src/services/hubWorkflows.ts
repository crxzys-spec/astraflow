import { HubWorkflowsApi } from "../client/apis/hub-workflows-api";
import type {
  HubWorkflowImportRequest,
  HubWorkflowImportResponse,
  HubWorkflowListResponse,
  HubWorkflowSummary,
} from "../client/models";
import { createApi } from "../api/client";
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

export const hubWorkflowsGateway = {
  list: listHubWorkflows,
  import: importHubWorkflow,
};
