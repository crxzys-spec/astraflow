import type { QueryClient } from "@tanstack/react-query";
import type { AxiosResponse } from "axios";

import type { Run } from "../api/models/run";
import type { Workflow } from "../api/models/workflow";
import type { WorkflowNodeState } from "../api/models/workflowNodeState";
import type { RunArtifact } from "../api/models/runArtifact";
import type { RunList } from "../api/models/runList";
import type { RunNodeStatus } from "../api/models/runNodeStatus";
import type { RunRef } from "../api/models/runRef";
import type { NodeResultDeltaEvent } from "../api/models/nodeResultDeltaEvent";
import { getGetRunDefinitionQueryKey, getGetRunQueryKey } from "../api/endpoints";
import { useWorkflowStore } from "../features/workflow";
import type { WorkflowNodeStateUpdateMap } from "../features/workflow";

const RUNS_QUERY_PREFIX = "/api/v1/runs";

type RunMutator = (run: Run) => Run;

const applyMutator = (run: Run, mutator: RunMutator): Run => {
  const next = mutator(run);
  return next === run ? run : { ...next };
};

export const upsertRunCaches = (queryClient: QueryClient, run: Run | RunRef) => {
  const normalizedRun: Run = {
    runId: run.runId,
    status: run.status,
    definitionHash: (run as Run).definitionHash ?? "",
    clientId: (run as Run).clientId ?? "",
    startedAt: (run as Run).startedAt ?? null,
    finishedAt: (run as Run).finishedAt ?? null,
    error: (run as Run).error,
    artifacts: (run as Run).artifacts,
    nodes: (run as Run).nodes,
  };

  const runKey = getGetRunQueryKey(run.runId);
  queryClient.setQueryData<AxiosResponse<Run>>(runKey, (existing) => ({
    ...existing,
    data: normalizedRun,
  }));

  const matchingLists = queryClient.getQueriesData<AxiosResponse<RunList>>({
    queryKey: [RUNS_QUERY_PREFIX],
  });

  matchingLists.forEach(([queryKey, response]) => {
    const items = response?.data?.items ?? [];
    const index = items.findIndex((item) => item.runId === run.runId);
    const nextItems =
      index === -1
        ? [normalizedRun, ...items]
        : items.map((item, idx) => (idx === index ? { ...item, ...normalizedRun } : item));
    queryClient.setQueryData(queryKey, {
      ...response,
      data: {
        ...(response?.data ?? { items: [] }),
        items: nextItems,
      },
    });
  });
};

export const updateRunCaches = (
  queryClient: QueryClient,
  runId: string,
  mutator: RunMutator,
) => {
  const runKey = getGetRunQueryKey(runId);
  queryClient.setQueryData<AxiosResponse<Run>>(runKey, (existing) => {
    if (!existing?.data) {
      return existing;
    }
    const updatedRun = applyMutator(existing.data, mutator);
    if (updatedRun === existing.data) {
      return existing;
    }
    return {
      ...existing,
      data: updatedRun,
    };
  });

  const matchingLists = queryClient.getQueriesData<AxiosResponse<RunList>>({
    queryKey: [RUNS_QUERY_PREFIX],
  });

  matchingLists.forEach(([queryKey, response]) => {
    if (!response?.data?.items?.length) {
      return;
    }
    const index = response.data.items.findIndex((item) => item.runId === runId);
    if (index === -1) {
      return;
    }
    const candidate = response.data.items[index];
    const updatedRun = applyMutator(candidate, mutator);
    if (updatedRun === candidate) {
      return;
    }
    const nextItems = response.data.items.slice();
    nextItems[index] = updatedRun;
    queryClient.setQueryData(queryKey, {
      ...response,
      data: {
        ...response.data,
        items: nextItems,
      },
    });
  });
};

export const replaceRunSnapshot = (
  queryClient: QueryClient,
  runId: string,
  snapshot: Run,
  nodes?: RunNodeStatus[] | null,
) => {
  updateRunCaches(queryClient, runId, (run) => ({
    ...run,
    ...snapshot,
    nodes: nodes ?? snapshot.nodes ?? run.nodes,
  }));
};

type NodeMutator = (node: RunNodeStatus) => RunNodeStatus;

export const updateRunNode = (
  queryClient: QueryClient,
  runId: string,
  nodeId: string,
  mutator: NodeMutator,
) => {
  updateRunCaches(queryClient, runId, (run) => {
    if (!run.nodes?.length) {
      return run;
    }
    const nodeIndex = run.nodes.findIndex((node) => node.nodeId === nodeId);
    if (nodeIndex === -1) {
      return run;
    }
    const currentNode = run.nodes[nodeIndex];
    const nextNode = mutator(currentNode);
    if (nextNode === currentNode) {
      return run;
    }
    const nextNodes = run.nodes.slice();
    nextNodes[nodeIndex] = nextNode;
    return {
      ...run,
      nodes: nextNodes,
    };
  });
};

const cloneWorkflowState = (state: WorkflowNodeState | null | undefined) =>
  state == null ? undefined : (JSON.parse(JSON.stringify(state)) as WorkflowNodeState);

const cloneResultRecord = (
  value: Record<string, unknown> | null | undefined,
): Record<string, unknown> | null | undefined => {
  if (value === undefined) {
    return undefined;
  }
  if (value === null) {
    return null;
  }
  return JSON.parse(JSON.stringify(value)) as Record<string, unknown>;
};

const cloneRuntimeArtifacts = (artifacts: RunArtifact[] | null | undefined) => {
  if (artifacts === undefined) {
    return undefined;
  }
  if (artifacts === null) {
    return null;
  }
  return JSON.parse(JSON.stringify(artifacts)) as RunArtifact[];
};

const valuesEqual = (left: unknown, right: unknown) => {
  if (left === right) {
    return true;
  }
  if (left === undefined || right === undefined) {
    return left === right;
  }
  return JSON.stringify(left) === JSON.stringify(right);
};

const decodePointerSegment = (segment: string) => segment.replace(/~1/g, "/").replace(/~0/g, "~");

const splitJsonPointer = (pointer?: string | null): string[] | null => {
  if (!pointer || !pointer.startsWith("/")) {
    return null;
  }
  const segments = pointer
    .split("/")
    .slice(1)
    .map((part) => decodePointerSegment(part))
    .filter((part) => part.length > 0);
  return segments.length ? segments : null;
};

const findDraftNode = (
  nodeId: string,
  store: ReturnType<typeof useWorkflowStore.getState> | null,
): any => {
  if (!store) {
    return undefined;
  }
  const searchWorkflow = (workflow?: { nodes: Record<string, any> }) => {
    if (!workflow?.nodes) {
      return undefined;
    }
    const direct = workflow.nodes[nodeId];
    if (direct) {
      return direct;
    }
    for (const candidate of Object.values(workflow.nodes)) {
      const middleware = (candidate as { middlewares?: { id: string }[] }).middlewares?.find(
        (mw) => mw.id === nodeId,
      );
      if (middleware) {
        return middleware;
      }
    }
    return undefined;
  };

  const rootNode = searchWorkflow(store.workflow);
  if (rootNode) {
    return rootNode;
  }
  for (const entry of store.subgraphDrafts) {
    const candidate = searchWorkflow(entry.definition);
    if (candidate) {
      return candidate;
    }
  }
  return undefined;
};

type JsonPatchOp = {
  op?: string;
  path?: string;
  from?: string;
  value?: unknown;
};

const applyPointerOperation = (
  target: unknown,
  segments: string[],
  op: "append" | "replace" | "remove",
  value: unknown,
): { root: unknown; changed: boolean } => {
  if (!segments.length) {
    return { root: target, changed: false };
  }
  const root = Array.isArray(target)
    ? [...target]
    : target && typeof target === "object"
      ? { ...(target as Record<string, unknown>) }
      : {};
  let cursor: any = root;
  for (let i = 0; i < segments.length - 1; i += 1) {
    const key = segments[i];
    const isIndex = /^\d+$/.test(key);
    if (Array.isArray(cursor)) {
      const index = isIndex ? Number.parseInt(key, 10) : 0;
      if (!Number.isFinite(index)) {
        return { root, changed: false };
      }
      if (cursor[index] == null || typeof cursor[index] !== "object") {
        cursor[index] = {};
      }
      cursor = cursor[index];
    } else {
      if (!cursor || typeof cursor !== "object") {
        return { root, changed: false };
      }
      if (!(key in cursor) || cursor[key] == null || typeof cursor[key] !== "object") {
        cursor[key] = {};
      }
      cursor = cursor[key];
    }
  }
  const leafKey = segments[segments.length - 1];
  let changed = false;
  const isIndex = /^\d+$/.test(leafKey);
  if (op === "remove") {
    if (Array.isArray(cursor) && isIndex) {
      const index = Number.parseInt(leafKey, 10);
      if (Number.isFinite(index) && index >= 0 && index < cursor.length) {
        cursor.splice(index, 1);
        changed = true;
      }
    } else if (cursor && typeof cursor === "object" && leafKey in cursor) {
      delete cursor[leafKey];
      changed = true;
    }
    return { root, changed };
  }

  if (op === "append") {
    const slot = cursor && typeof cursor === "object" ? (cursor as Record<string, unknown>)[leafKey] : undefined;
    const arr = Array.isArray(slot) ? slot.slice() : [];
    arr.push(value);
    if (Array.isArray(cursor) && isIndex) {
      const index = Number.parseInt(leafKey, 10);
      if (Number.isFinite(index)) {
        cursor[index] = arr;
        changed = true;
      }
    } else if (cursor && typeof cursor === "object") {
      if (!valuesEqual(slot, arr)) {
        (cursor as Record<string, unknown>)[leafKey] = arr;
        changed = true;
      }
    }
    return { root, changed };
  }

  if (op === "replace") {
    if (Array.isArray(cursor) && isIndex) {
      const index = Number.parseInt(leafKey, 10);
      if (Number.isFinite(index)) {
        if (!valuesEqual(cursor[index], value)) {
          cursor[index] = value;
          changed = true;
        }
      }
    } else if (cursor && typeof cursor === "object") {
      if (!valuesEqual((cursor as Record<string, unknown>)[leafKey], value)) {
        (cursor as Record<string, unknown>)[leafKey] = value;
        changed = true;
      }
    }
  }
  return { root, changed };
};

const applyJsonPatchOperations = (target: unknown, patches: JsonPatchOp[]): { next: unknown; changed: boolean } => {
  let current = target;
  let changed = false;
  patches.forEach((patch) => {
    const op = (patch.op || "").toLowerCase();
    const segments = splitJsonPointer(patch.path);
    if (!segments) {
      return;
    }
    if (op === "add" || op === "replace") {
      const result = applyPointerOperation(current, segments, "replace", patch.value);
      current = result.root;
      changed = changed || result.changed;
    } else if (op === "remove") {
      const result = applyPointerOperation(current, segments, "remove", undefined);
      current = result.root;
      changed = changed || result.changed;
    }
  });
  return { next: current, changed };
};

const extractDeltaValue = (payload?: Record<string, unknown> | null): unknown => {
  if (!payload || typeof payload !== "object") {
    return undefined;
  }
  if ("value" in payload) {
    return (payload as { value?: unknown }).value;
  }
  return payload;
};

const applyResultDelta = (
  current: Record<string, unknown> | null | undefined,
  delta: Pick<NodeResultDeltaEvent, "operation" | "path" | "payload" | "patches">,
): { next: Record<string, unknown> | null; changed: boolean } => {
  const base =
    current && typeof current === "object" && !Array.isArray(current)
      ? (JSON.parse(JSON.stringify(current)) as Record<string, unknown>)
      : {};

  if (delta.operation === "patch" && Array.isArray(delta.patches)) {
    const patched = applyJsonPatchOperations(base, delta.patches as JsonPatchOp[]);
    return {
      next: (patched.next as Record<string, unknown>) ?? {},
      changed: patched.changed,
    };
  }

  const segments = splitJsonPointer(delta.path);
  if (!segments) {
    return { next: base, changed: false };
  }
  const op = (delta.operation as string | undefined) ?? "replace";
  const value = extractDeltaValue(delta.payload ?? undefined);
  const result = applyPointerOperation(base, segments, op === "append" ? "append" : op === "remove" ? "remove" : "replace", value);
  return { next: result.root as Record<string, unknown>, changed: result.changed };
};

type WorkflowNodeRuntimeUpdate = {
  result?: Record<string, unknown> | null;
  artifacts?: RunArtifact[] | null;
  summary?: string | null;
};

const updateWorkflowDefinitionNodeStates = (
  queryClient: QueryClient,
  runId: string,
  updates: WorkflowNodeStateUpdateMap,
  syncToStore = true,
) => {
  if (!Object.keys(updates).length) {
    return;
  }
  const definitionKey = getGetRunDefinitionQueryKey(runId);
  queryClient.setQueryData<AxiosResponse<Workflow>>(definitionKey, (existing) => {
    if (!existing?.data?.nodes?.length) {
      return existing;
    }
    let changed = false;
    const nextNodes = existing.data.nodes.map((node) => {
      if (!(node.id in updates)) {
        return node;
      }
      const update = updates[node.id] ?? undefined;
      const nextState = cloneWorkflowState(update);
      const currentState = node.state ?? undefined;
      const same =
        JSON.stringify(currentState ?? null) === JSON.stringify(nextState ?? null);
      if (same) {
        return node;
      }
      changed = true;
      return {
        ...node,
        state: nextState,
      };
    });
    if (!changed) {
      return existing;
    }
    return {
      ...existing,
      data: {
        ...existing.data,
        nodes: nextNodes,
      },
    };
  });
  if (syncToStore) {
    useWorkflowStore.getState().updateNodeStates(updates);
  }
};

const updateWorkflowDefinitionNodeRuntime = (
  queryClient: QueryClient,
  runId: string,
  updates: Record<string, WorkflowNodeRuntimeUpdate>,
  syncToStore = true,
) => {
  if (!Object.keys(updates).length) {
    return;
  }
  const definitionKey = getGetRunDefinitionQueryKey(runId);
  const effectiveUpdates: Record<string, WorkflowNodeRuntimeUpdate> = {};
  const storeInstance = syncToStore ? useWorkflowStore.getState() : null;

  const applyMiddlewareRuntimeUpdate = (
    mw: Workflow["nodes"][number]["middlewares"][number],
  ): { next: Workflow["nodes"][number]["middlewares"][number]; changed: boolean } => {
    const update = updates[mw.id];
    if (!update) {
      return { next: mw, changed: false };
    }
    const currentResult = (mw as unknown as { results?: Record<string, unknown> | null }).results ?? {};
    const currentArtifacts = (mw as unknown as { artifacts?: RunArtifact[] | null }).artifacts ?? null;
    const currentSummary =
      (mw as unknown as { metadata?: Record<string, unknown> | null }).metadata?.summary ?? null;

    const nextResult = cloneResultRecord(update.result);
    const nextArtifacts = cloneRuntimeArtifacts(update.artifacts);
    const nextSummary = update.summary !== undefined ? update.summary ?? null : currentSummary;

    const willUpdateResult = nextResult !== undefined && !valuesEqual(currentResult, nextResult);
    const willUpdateArtifacts =
      update?.artifacts !== undefined && !valuesEqual(currentArtifacts ?? undefined, nextArtifacts);
    const willUpdateSummary =
      update?.summary !== undefined && !valuesEqual(currentSummary ?? undefined, nextSummary);

    if (!willUpdateResult && !willUpdateArtifacts && !willUpdateSummary) {
      return { next: mw, changed: false };
    }

    const baseMetadata = (mw as unknown as { metadata?: Record<string, unknown> | null }).metadata;
    const nextMw = {
      ...mw,
      results: willUpdateResult ? nextResult ?? {} : currentResult,
      artifacts: willUpdateArtifacts ? nextArtifacts ?? null : currentArtifacts,
      metadata: willUpdateSummary
        ? { ...(baseMetadata ?? {}), summary: nextSummary ?? undefined }
        : baseMetadata,
    };
    effectiveUpdates[mw.id] = {
      ...(willUpdateResult
        ? {
            result:
              update.result === undefined
                ? undefined
                : update.result === null
                ? null
                : (JSON.parse(JSON.stringify(update.result)) as Record<string, unknown>),
          }
        : {}),
      ...(willUpdateArtifacts ? { artifacts: nextArtifacts ?? null } : {}),
      ...(willUpdateSummary ? { summary: nextSummary ?? null } : {}),
    };
    return { next: nextMw, changed: true };
  };

  const applyNodeRuntimeUpdate = (
    node: Workflow["nodes"][number],
  ): { next: Workflow["nodes"][number]; changed: boolean } => {
    const update = updates[node.id];
    let changed = false;
    const currentResult =
      (node as unknown as { results?: Record<string, unknown> | null }).results ?? {};
    const currentArtifacts =
      (node as unknown as { artifacts?: RunArtifact[] | null }).artifacts ?? null;
    const currentSummary =
      (node as unknown as { metadata?: Record<string, unknown> | null }).metadata?.summary ?? null;

    const nextResult = cloneResultRecord(update.result);
    const nextArtifacts = cloneRuntimeArtifacts(update.artifacts);
    const nextSummary = update?.summary !== undefined ? update.summary ?? null : currentSummary;

    const willUpdateResult =
      nextResult !== undefined && !valuesEqual(currentResult, nextResult);
    const willUpdateArtifacts =
      update?.artifacts !== undefined && !valuesEqual(currentArtifacts ?? undefined, nextArtifacts);
    const willUpdateSummary =
      update?.summary !== undefined && !valuesEqual(currentSummary ?? undefined, nextSummary);

    if (update) {
      if (willUpdateResult) {
        effectiveUpdates[node.id] = {
          ...effectiveUpdates[node.id],
          result:
            update.result === undefined
              ? undefined
              : update.result === null
              ? null
              : (JSON.parse(JSON.stringify(update.result)) as Record<string, unknown>),
        };
        changed = true;
      }
      if (willUpdateArtifacts) {
        effectiveUpdates[node.id] = {
          ...effectiveUpdates[node.id],
          artifacts: nextArtifacts ?? null,
        };
        changed = true;
      }
      if (willUpdateSummary) {
        effectiveUpdates[node.id] = {
          ...effectiveUpdates[node.id],
          summary: nextSummary ?? null,
        };
        changed = true;
      }
    }

    let middlewareChanged = false;
    const nextMiddlewares = node.middlewares?.map((mw) => {
      const res = applyMiddlewareRuntimeUpdate(mw);
      if (res.changed) {
        middlewareChanged = true;
      }
      return res.next;
    });
    if (middlewareChanged) {
      changed = true;
    }

    return {
      next: {
        ...node,
        results: willUpdateResult ? nextResult ?? {} : currentResult,
        artifacts: willUpdateArtifacts ? nextArtifacts ?? null : currentArtifacts,
        metadata: willUpdateSummary
          ? { ...(node.metadata ?? {}), summary: nextSummary ?? undefined }
          : node.metadata,
        middlewares: middlewareChanged ? nextMiddlewares : node.middlewares,
      },
      changed,
    };
  };

  const applyRuntimeUpdatesToWorkflow = (
    workflow: Workflow,
  ): { workflow: Workflow; changed: boolean } => {
    let nodesChanged = false;
    const nextNodes = workflow.nodes.map((node) => {
      const result = applyNodeRuntimeUpdate(node);
      if (result.changed) {
        nodesChanged = true;
      }
      return result.next;
    });

    let subgraphsChanged = false;
    const nextSubgraphs = workflow.subgraphs?.length
      ? workflow.subgraphs.map((subgraph) => {
          const result = applyRuntimeUpdatesToWorkflow(subgraph.definition);
          if (result.changed) {
            subgraphsChanged = true;
            return {
              ...subgraph,
              definition: result.workflow,
            };
          }
          return subgraph;
        })
      : workflow.subgraphs;

    if (!nodesChanged && !subgraphsChanged) {
      return { workflow, changed: false };
    }

    return {
      workflow: {
        ...workflow,
        nodes: nodesChanged ? nextNodes : workflow.nodes,
        subgraphs: subgraphsChanged ? nextSubgraphs : workflow.subgraphs,
      },
      changed: true,
    };
  };

  queryClient.setQueryData<AxiosResponse<Workflow>>(definitionKey, (existing) => {
    if (!existing?.data) {
      return existing;
    }
    const result = applyRuntimeUpdatesToWorkflow(existing.data);
    if (!result.changed) {
      return existing;
    }
    return {
      ...existing,
      data: result.workflow,
    };
  });

  if (!storeInstance) {
    return;
  }

  const storePayload: Record<string, WorkflowNodeRuntimeUpdate> = { ...effectiveUpdates };
  Object.entries(updates).forEach(([nodeId, update]) => {
    if (storePayload[nodeId]) {
      return;
    }
    const node = findDraftNode(nodeId, storeInstance);
    if (!node) {
      return;
    }
    const candidate: WorkflowNodeRuntimeUpdate = {};
    if (update.result !== undefined) {
      const nextResult = cloneResultRecord(update.result);
      const currentResult = (node as { results?: Record<string, unknown> | null }).results ?? {};
      if (nextResult !== undefined && !valuesEqual(currentResult, nextResult)) {
        candidate.result =
          update.result === null
            ? null
            : (JSON.parse(JSON.stringify(update.result)) as Record<string, unknown>);
      }
    }
    if (update.artifacts !== undefined) {
      const nextArtifacts = cloneRuntimeArtifacts(update.artifacts);
      const currentArtifacts =
        (node as { runtimeArtifacts?: RunArtifact[] | null }).runtimeArtifacts ??
        (node as { artifacts?: RunArtifact[] | null }).artifacts ??
        null;
      if (!valuesEqual(currentArtifacts ?? undefined, nextArtifacts)) {
        candidate.artifacts = nextArtifacts ?? null;
      }
    }
    if (update.summary !== undefined) {
      const nextSummary = update.summary ?? null;
      const currentSummary =
        (node as { runtimeSummary?: string | null }).runtimeSummary ??
        ((node as { metadata?: Record<string, unknown> | null }).metadata?.summary ?? null);
      if (!valuesEqual(currentSummary ?? undefined, nextSummary)) {
        candidate.summary = nextSummary;
      }
    }
    if (Object.keys(candidate).length > 0) {
      storePayload[nodeId] = candidate;
    }
  });

  if (Object.keys(storePayload).length > 0) {
    Object.entries(storePayload).forEach(([nodeId, data]) => {
      storeInstance.updateNodeRuntime(nodeId, data);
    });
  }
};

export const applyNodeResultDelta = (
  queryClient: QueryClient,
  runId: string,
  nodeId: string,
  delta: Pick<NodeResultDeltaEvent, "operation" | "path" | "payload" | "patches" | "nodeId">,
  syncToStore = true,
) => {
  const definitionKey = getGetRunDefinitionQueryKey(runId);
  const storeInstance = syncToStore ? useWorkflowStore.getState() : null;

  const existingNode = findDraftNode(nodeId, storeInstance);
  const existingStoreResult =
    (existingNode as { results?: Record<string, unknown> | null } | undefined)?.results;

  const definition = queryClient.getQueryData<AxiosResponse<Workflow>>(definitionKey)?.data;
  const findResultInWorkflow = (workflow?: Workflow): Record<string, unknown> | null | undefined => {
    if (!workflow) {
      return undefined;
    }
    const node = workflow.nodes?.find((entry) => entry.id === nodeId);
    if (node) {
      return (node as { results?: Record<string, unknown> | null }).results ?? undefined;
    }
    for (const subgraph of workflow.subgraphs ?? []) {
      const nested = findResultInWorkflow(subgraph.definition);
      if (nested !== undefined) {
        return nested;
      }
    }
    return undefined;
  };
  const existingDefinitionResult = findResultInWorkflow(definition);

  const baseResult = existingStoreResult ?? existingDefinitionResult ?? {};
  const { next, changed } = applyResultDelta(baseResult, delta);
  if (!changed) {
    return;
  }
  updateWorkflowDefinitionNodeRuntime(
    queryClient,
    runId,
    { [nodeId]: { result: next ?? {} } },
    syncToStore,
  );
};

const STAGE_PRIORITY: Record<string, number> = {
  queued: 1,
  running: 2,
  succeeded: 3,
  failed: 4,
  cancelled: 4,
};

const normaliseStage = (stage?: string | null): string | undefined =>
  typeof stage === "string" ? stage.toLowerCase() : undefined;

const getStagePriority = (stage?: string | null): number => {
  const normalised = normaliseStage(stage);
  if (!normalised) {
    return 0;
  }
  return STAGE_PRIORITY[normalised] ?? 0;
};

const getTimestamp = (value?: string | null): number => {
  if (!value) {
    return 0;
  }
  const parsed = Date.parse(value);
  return Number.isNaN(parsed) ? 0 : parsed;
};

const isNewerState = (next?: WorkflowNodeState | null, current?: WorkflowNodeState | null): boolean =>
  getTimestamp(next?.lastUpdatedAt ?? null) > getTimestamp(current?.lastUpdatedAt ?? null);

const withFallbackLastUpdatedAt = <T extends WorkflowNodeState | null | undefined>(
  state: T,
  fallback?: string | null
): T => {
  if (!state) {
    return state;
  }
  if (state.lastUpdatedAt) {
    return state;
  }
  const fallbackValue = fallback ?? new Date().toISOString();
  if (!fallbackValue) {
    return state;
  }
  return { ...state, lastUpdatedAt: fallbackValue } as T;
};

const findCurrentNodeState = (
  store: ReturnType<typeof useWorkflowStore.getState>,
  nodeId: string
): WorkflowNodeState | undefined => {
  const searchWorkflow = (workflow?: { nodes?: Record<string, unknown> }) => {
    if (!workflow?.nodes) {
      return undefined;
    }
    const node = (workflow.nodes as Record<string, { id?: string; state?: WorkflowNodeState }>)[nodeId];
    if (node?.state) {
      return node.state;
    }
    for (const candidate of Object.values(workflow.nodes)) {
      const middleware = (candidate as { middlewares?: { id: string; state?: WorkflowNodeState }[] })
        ?.middlewares?.find((mw) => mw.id === nodeId);
      if (middleware?.state) {
        return middleware.state;
      }
    }
    return undefined;
  };

  const rootState = searchWorkflow(store.workflow);
  if (rootState) {
    return rootState;
  }
  for (const entry of store.subgraphDrafts ?? []) {
    const candidate = searchWorkflow(entry.definition);
    if (candidate) {
      return candidate;
    }
  }
  return undefined;
};

export const updateRunDefinitionNodeState = (
  queryClient: QueryClient,
  runId: string,
  nodeId: string,
  state: WorkflowNodeState | null | undefined,
  occurredAt?: string,
  syncToStore = true,
) => {
  const storeInstance = syncToStore ? useWorkflowStore.getState() : null;
  const currentState = storeInstance ? findCurrentNodeState(storeInstance, nodeId) : undefined;
  const nextState = withFallbackLastUpdatedAt(state, occurredAt);
  if (nextState == null) {
    if (!currentState) {
      return;
    }
    const currentPriority = getStagePriority(currentState.stage);
    if (currentPriority > 0) {
      return;
    }
    return;
  }
  const nextPriority = getStagePriority(nextState.stage);
  const currentPriority = getStagePriority(currentState?.stage);
  const newer = isNewerState(nextState, currentState);
  const stageChanged = normaliseStage(nextState.stage) !== normaliseStage(currentState?.stage);
  if (currentPriority && nextPriority < currentPriority && !newer && !stageChanged) {
    return;
  }
  const updates: WorkflowNodeStateUpdateMap = { [nodeId]: nextState };
  updateWorkflowDefinitionNodeStates(queryClient, runId, updates, syncToStore);
};

export const updateRunDefinitionNodeRuntime = (
  queryClient: QueryClient,
  runId: string,
  nodeId: string,
  runtime: WorkflowNodeRuntimeUpdate,
  syncToStore = true,
) => {
  updateWorkflowDefinitionNodeRuntime(
    queryClient,
    runId,
    {
      [nodeId]: runtime,
    },
    syncToStore,
  );
};

export const updateRunNodeResultDelta = (
  queryClient: QueryClient,
  runId: string,
  nodeId: string,
  delta: Pick<NodeResultDeltaEvent, "operation" | "path" | "payload" | "patches" | "nodeId">,
) => {
  const runKey = getGetRunQueryKey(runId);
  queryClient.setQueryData<AxiosResponse<Run>>(runKey, (existing) => {
    const run = existing?.data;
    if (!run?.nodes?.length) {
      return existing;
    }
    let changed = false;
    const applyToNode = (node: RunNodeStatus) => {
      const current = (node.result as Record<string, unknown> | null | undefined) ?? {};
      const result = applyResultDelta(current, delta);
      if (!result.changed) {
        return node;
      }
      changed = true;
      return { ...node, result: result.next ?? {} };
    };
    const nextNodes = run.nodes.map((node) => {
      if (node.nodeId === nodeId) {
        return applyToNode(node);
      }
      const middlewares = (node as { middlewares?: { id?: string; result?: unknown }[] }).middlewares;
      if (!middlewares?.length) {
        return node;
      }
      let mwChanged = false;
      const nextMws = middlewares.map((mw) => {
        if (mw.id !== nodeId) {
          return mw;
        }
        const current = (mw.result as Record<string, unknown> | null | undefined) ?? {};
        const result = applyResultDelta(current, delta);
        if (!result.changed) {
          return mw;
        }
        mwChanged = true;
        return { ...mw, result: result.next ?? {} };
      });
      if (!mwChanged) {
        return node;
      }
      changed = true;
      return { ...node, middlewares: nextMws };
    });
    if (!changed) {
      return existing;
    }
    return {
      ...existing,
      data: {
        ...run,
        nodes: nextNodes,
      },
    };
  });
};

export const applyRunDefinitionSnapshot = (
  queryClient: QueryClient,
  runId: string,
  nodes: RunNodeStatus[] | null | undefined,
  occurredAt?: string,
  syncToStore = true,
) => {
  if (!nodes?.length) {
    return;
  }
  const storeInstance = syncToStore ? useWorkflowStore.getState() : null;
  const currentStateById = new Map<string, WorkflowNodeState | undefined>();
  const indexStates = (workflow?: { nodes?: Record<string, unknown> }) => {
    if (!workflow?.nodes) {
      return;
    }
    Object.values(workflow.nodes).forEach((node) => {
      const castNode = node as { id?: string; state?: WorkflowNodeState; middlewares?: { id: string; state?: WorkflowNodeState }[] };
      if (castNode.id) {
        currentStateById.set(castNode.id, castNode.state);
      }
      castNode.middlewares?.forEach((mw) => {
        if (mw.id) {
          currentStateById.set(mw.id, mw.state);
        }
      });
    });
  };
  if (storeInstance) {
    indexStates(storeInstance.workflow);
    storeInstance.subgraphDrafts?.forEach((entry) => indexStates(entry.definition));
  }

  const stateUpdates: WorkflowNodeStateUpdateMap = {};
  nodes.forEach((node) => {
    const rawNextState = (node.state as WorkflowNodeState | undefined) ?? undefined;
    const nextState = withFallbackLastUpdatedAt(rawNextState, occurredAt);
    if (!nextState) {
      return;
    }
    const nextStage = nextState.stage;
    const currentState = currentStateById.get(node.nodeId);
    if (currentState) {
      const currentStage = currentState.stage;
      const currentPriority = getStagePriority(currentStage);
      const nextPriority = getStagePriority(nextStage);
      const newer = isNewerState(nextState, currentState);
      const stageChanged = normaliseStage(nextStage) !== normaliseStage(currentStage);
      if (currentPriority > 0 && nextPriority === 0 && !newer && !stageChanged) {
        return;
      }
      if (nextPriority < currentPriority && !newer && !stageChanged) {
        return;
      }
    }
    stateUpdates[node.nodeId] = nextState;

    // Capture middleware states, if present on the runtime payload.
    const middlewares = (node as { middlewares?: { id?: string; state?: WorkflowNodeState }[] }).middlewares;
    middlewares?.forEach((mw) => {
      if (!mw?.id) {
        return;
      }
      const mwNextState = withFallbackLastUpdatedAt(
        (mw.state as WorkflowNodeState | undefined) ?? undefined,
        occurredAt,
      );
      if (!mwNextState) {
        return;
      }
      const currentMwState = currentStateById.get(mw.id);
      if (currentMwState) {
        const currentPriority = getStagePriority(currentMwState.stage);
        const nextPriority = getStagePriority(mwNextState.stage);
        const newer = isNewerState(mwNextState, currentMwState);
        const stageChanged =
          normaliseStage(mwNextState.stage) !== normaliseStage(currentMwState.stage);
        if (currentPriority > 0 && nextPriority === 0 && !newer && !stageChanged) {
          return;
        }
        if (nextPriority < currentPriority && !newer && !stageChanged) {
          return;
        }
      }
      stateUpdates[mw.id] = mwNextState;
    });
  });
  const runtimeUpdates = nodes.reduce<Record<string, WorkflowNodeRuntimeUpdate>>((acc, node) => {
    const payload: WorkflowNodeRuntimeUpdate = {};
    if (node.result !== undefined) {
      payload.result = (node.result as Record<string, unknown> | null) ?? null;
    }
    if (node.artifacts !== undefined) {
      payload.artifacts = node.artifacts ?? null;
    }
    if (node.metadata && "summary" in node.metadata) {
      const summary = (node.metadata as Record<string, unknown>).summary;
      if (typeof summary === "string" || summary === null) {
        payload.summary = summary ?? null;
      }
    }
    if (Object.keys(payload).length > 0) {
      acc[node.nodeId] = payload;
    }

    // Middleware runtime updates nested in the node payload.
    const middlewares = (node as { middlewares?: any[] }).middlewares;
    middlewares?.forEach((mw) => {
      const mwId = (mw as { id?: string }).id;
      if (!mwId) {
        return;
      }
      const mwPayload: WorkflowNodeRuntimeUpdate = {};
      if ((mw as { result?: unknown }).result !== undefined) {
        mwPayload.result = ((mw as { result?: unknown }).result as Record<string, unknown> | null) ?? null;
      }
      if ((mw as { artifacts?: unknown }).artifacts !== undefined) {
        mwPayload.artifacts = (mw as { artifacts?: unknown }).artifacts ?? null;
      }
      const mwSummary = (mw as { metadata?: { summary?: string | null } }).metadata?.summary;
      if (mwSummary !== undefined) {
        mwPayload.summary = mwSummary ?? null;
      }
      if (Object.keys(mwPayload).length > 0) {
        acc[mwId] = mwPayload;
      }
    });

    return acc;
  }, {});

  if (Object.keys(stateUpdates).length) {
    updateWorkflowDefinitionNodeStates(queryClient, runId, stateUpdates, syncToStore);
  }
  if (Object.keys(runtimeUpdates).length) {
    updateWorkflowDefinitionNodeRuntime(queryClient, runId, runtimeUpdates, syncToStore);
  }
};





