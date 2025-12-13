import { RunsApi } from "../client/apis/runs-api";
import type {
  Run,
  RunList,
  RunRef,
  RunStatus as ApiRunStatus,
  RunStartRequest,
  RunNodeStatus,
  Workflow,
} from "../client/models";
import { createApi } from "../api/client";
import { apiRequest } from "../api/fetcher";
import { toListModel } from "../lib/normalize";

const runsApi = createApi(RunsApi);

const toApiStatus = (status: RunStatusModel | null | undefined): ApiRunStatus | undefined =>
  status ?? undefined;

export type RunQueryParams = {
  limit?: number;
  cursor?: string;
  status?: RunStatusModel;
  clientId?: string;
};

export type RunRequestOptions = {
  dedupeKey?: string;
  signal?: AbortSignal;
};

export type RunModel = Omit<Run, "runId" | "status" | "startedAt" | "finishedAt" | "nodes"> & {
  runId: string;
  status: ApiRunStatus;
  startedAt: string | null;
  finishedAt: string | null;
  nodes: RunNodeStatus[];
};

export type RunListModel = {
  items: RunModel[];
  nextCursor: string | null;
};

export type RunDefinitionModel = Workflow | null;
export type RunStatusModel = ApiRunStatus;
export type RunStartPayload = RunStartRequest;
export type RunNodeStatusModel = RunNodeStatus;

export const normalizeRun = (run: Run | RunModel): RunModel => ({
  ...run,
  runId: run.runId ?? "",
  clientId: run.clientId ?? "",
  definitionHash: run.definitionHash ?? "",
  status: (run.status ?? "queued") as RunModel["status"],
  startedAt: run.startedAt ?? null,
  finishedAt: run.finishedAt ?? null,
  nodes: run.nodes ?? [],
});

const fromApiRun = (run: Run): RunModel => normalizeRun(run);

const fromApiRunList = (payload: RunList): RunListModel =>
  toListModel(payload, normalizeRun);

const fromApiRunRef = (ref: RunRef): RunModel =>
  normalizeRun({
    runId: ref.runId ?? "",
    status: (ref.status ?? "queued") as RunModel["status"],
    clientId: ref.clientId ?? "",
    definitionHash: ref.definitionHash ?? "",
    startedAt: null,
    finishedAt: null,
    nodes: [],
  } as Run);

const fromApiRunDefinition = (definition: Workflow | null | undefined): RunDefinitionModel =>
  (definition ?? null);

export const fetchRuns = async (
  params?: RunQueryParams,
  options?: RunRequestOptions,
): Promise<RunListModel> => {
  const response = await apiRequest(
    () => runsApi.listRuns(params?.limit, params?.cursor, toApiStatus(params?.status), params?.clientId),
    {
      dedupeKey: options?.dedupeKey,
      signal: options?.signal,
    },
  );
  return fromApiRunList(response.data);
};

export const fetchRun = async (runId: string, options?: RunRequestOptions): Promise<RunModel> => {
  const response = await apiRequest(() => runsApi.getRun(runId), {
    dedupeKey: options?.dedupeKey,
    signal: options?.signal,
  });
  return fromApiRun(response.data);
};

export const fetchRunDefinition = async (
  runId: string,
  options?: RunRequestOptions,
): Promise<RunDefinitionModel> => {
  const response = await apiRequest(() => runsApi.getRunDefinition(runId), {
    signal: options?.signal,
  });
  return fromApiRunDefinition(response.data);
};

export const startRun = async (
  payload: RunStartPayload,
  options?: { idempotencyKey?: string },
): Promise<RunModel> => {
  const response = await apiRequest(() => runsApi.startRun(payload, options?.idempotencyKey));
  return fromApiRunRef(response.data);
};

export const cancelRun = async (runId: string): Promise<void> => {
  await apiRequest(() => runsApi.cancelRun(runId, { signal: undefined }));
};

export const runsGateway = {
  list: fetchRuns,
  get: fetchRun,
  getDefinition: fetchRunDefinition,
  start: startRun,
  cancel: cancelRun,
};
