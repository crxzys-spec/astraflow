import { WorkflowsApi } from "../client/apis/workflows-api";
import type {
  Workflow,
  WorkflowList,
  WorkflowRef,
  WorkflowPreview,
} from "../client/models";
import { createApi } from "../api/client";
import { apiRequest } from "../api/fetcher";
import { toListModel } from "../lib/normalize";

const workflowsApi = createApi(WorkflowsApi);

export type WorkflowsQueryParams = {
  limit?: number;
  cursor?: string;
};

export type WorkflowRequestOptions = {
  dedupeKey?: string;
  signal?: AbortSignal;
};

export type WorkflowModel = Workflow & {
  id: string;
  metadata: NonNullable<Workflow["metadata"]> | Record<string, unknown>;
  previewImage?: string | null;
};

export type WorkflowListModel = {
  items: WorkflowModel[];
  nextCursor: string | null;
};

const normalizeWorkflow = (workflow: Workflow): WorkflowModel => ({
  ...workflow,
  id: workflow.id ?? "",
  metadata: workflow.metadata ?? {},
  previewImage: workflow.previewImage ?? null,
});

const fromApiWorkflow = (workflow: Workflow): WorkflowModel => normalizeWorkflow(workflow);

const fromApiWorkflowList = (payload: WorkflowList): WorkflowListModel =>
  toListModel(payload, normalizeWorkflow);

export const fetchWorkflows = async (
  params?: WorkflowsQueryParams,
  options?: WorkflowRequestOptions,
): Promise<WorkflowListModel> => {
  const response = await apiRequest<WorkflowList>(
    () => workflowsApi.listWorkflows(params?.limit, params?.cursor),
    { dedupeKey: options?.dedupeKey, signal: options?.signal },
  );
  return fromApiWorkflowList(response.data);
};

export const fetchWorkflow = async (workflowId: string, options?: WorkflowRequestOptions): Promise<WorkflowModel> => {
  const response = await apiRequest(() => workflowsApi.getWorkflow(workflowId), {
    dedupeKey: options?.dedupeKey,
    signal: options?.signal,
  });
  return fromApiWorkflow(response.data);
};

export const deleteWorkflow = async (workflowId: string): Promise<void> => {
  await apiRequest(() => workflowsApi.deleteWorkflow(workflowId));
};

export const persistWorkflow = async (
  workflow: Workflow,
  idempotencyKey?: string,
): Promise<WorkflowRef> => {
  const response = await apiRequest(() => workflowsApi.persistWorkflow(workflow, idempotencyKey));
  return response.data;
};

export const setWorkflowPreview = async (
  workflowId: string,
  data: { previewImage?: string | null },
): Promise<WorkflowPreview> => {
  const response = await apiRequest<WorkflowPreview>(() =>
    workflowsApi.setWorkflowPreview(workflowId, data),
  );
  return response.data;
};

export const workflowsGateway = {
  list: fetchWorkflows,
  get: fetchWorkflow,
  delete: deleteWorkflow,
  persist: persistWorkflow,
  setPreview: setWorkflowPreview,
};
