import { WorkersApi } from "../client/apis/workers-api";
import type { CommandRef, Worker, WorkerCommand, WorkerPackage, WorkerPackageStatus } from "../client/models";
import { createApi } from "../api/client";
import { apiRequest } from "../api/fetcher";
import { toListModel } from "../lib/normalize";

const workersApi = createApi(WorkersApi);

export type WorkerQueryParams = {
  queue?: string;
  connected?: boolean;
  registered?: boolean;
  healthy?: boolean;
  packageName?: string;
  packageVersion?: string;
  packageStatus?: WorkerPackageStatus;
  maxHeartbeatAgeSeconds?: number;
  maxInflight?: number;
  maxLatencyMs?: number;
  limit?: number;
  cursor?: string;
};

export type WorkerModel = Worker & {
  queues: string[];
  packages: WorkerPackage[];
  payloadTypes: string[];
};

export type WorkerListModel = {
  items: WorkerModel[];
  nextCursor: string | null;
};

export const normalizeWorker = (worker: Worker): WorkerModel => ({
  ...worker,
  queues: worker.queues ?? [],
  packages: worker.packages ?? [],
  payloadTypes: worker.payloadTypes ?? [],
});

const fromApiWorker = (worker: Worker): WorkerModel => normalizeWorker(worker);

const fromApiWorkerList = (payload: { items?: Worker[] | null; nextCursor?: string | null }): WorkerListModel =>
  toListModel(payload, normalizeWorker);

export const listWorkers = async (params?: WorkerQueryParams): Promise<WorkerListModel> => {
  const response = await apiRequest(() =>
    workersApi.listWorkers(
      params?.queue,
      params?.connected,
      params?.registered,
      params?.healthy,
      params?.packageName,
      params?.packageVersion,
      params?.packageStatus,
      params?.maxHeartbeatAgeSeconds,
      params?.maxInflight,
      params?.maxLatencyMs,
      params?.limit,
      params?.cursor,
    ),
  );
  return fromApiWorkerList(response.data);
};

export const getWorker = async (workerName: string): Promise<WorkerModel> => {
  const response = await apiRequest(() => workersApi.getWorker(workerName));
  return fromApiWorker(response.data);
};

export const sendWorkerCommand = async (
  workerName: string,
  command: WorkerCommand,
  idempotencyKey?: string,
): Promise<CommandRef> => {
  const response = await apiRequest(() => workersApi.sendWorkerCommand(workerName, command, idempotencyKey));
  return response.data;
};

export const workersGateway = {
  list: listWorkers,
  get: getWorker,
  command: sendWorkerCommand,
};
