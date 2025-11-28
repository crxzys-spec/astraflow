import type { QueryClient } from "@tanstack/react-query";
import type { AxiosResponse } from "axios";

import type { Run } from "../api/models/run";
import type { Workflow } from "../api/models/workflow";
import type { WorkflowNodeState } from "../api/models/workflowNodeState";
import type { RunArtifact } from "../api/models/runArtifact";
import type { RunList } from "../api/models/runList";
import type { RunNodeStatus } from "../api/models/runNodeStatus";
import type { RunRef } from "../api/models/runRef";
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

type WorkflowNodeRuntimeUpdate = {
  result?: Record<string, unknown> | null;
  artifacts?: RunArtifact[] | null;
  summary?: string | null;
};

const updateWorkflowDefinitionNodeStates = (
  queryClient: QueryClient,
  runId: string,
  updates: WorkflowNodeStateUpdateMap,
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
  useWorkflowStore.getState().updateNodeStates(updates);
};

const updateWorkflowDefinitionNodeRuntime = (
  queryClient: QueryClient,
  runId: string,
  updates: Record<string, WorkflowNodeRuntimeUpdate>,
) => {
  if (!Object.keys(updates).length) {
    return;
  }
  const definitionKey = getGetRunDefinitionQueryKey(runId);
  const effectiveUpdates: Record<string, WorkflowNodeRuntimeUpdate> = {};
  const storeInstance = useWorkflowStore.getState();

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

  const findDraftNode = (nodeId: string) => {
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

    const rootNode = searchWorkflow(storeInstance.workflow);
    if (rootNode) {
      return rootNode;
    }
    for (const entry of storeInstance.subgraphDrafts) {
      const candidate = searchWorkflow(entry.definition);
      if (candidate) {
        return candidate;
      }
    }
    return undefined;
  };

  const storePayload: Record<string, WorkflowNodeRuntimeUpdate> = { ...effectiveUpdates };
  Object.entries(updates).forEach(([nodeId, update]) => {
    if (storePayload[nodeId]) {
      return;
    }
    const node = findDraftNode(nodeId);
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

export const updateRunDefinitionNodeState = (
  queryClient: QueryClient,
  runId: string,
  nodeId: string,
  state: WorkflowNodeState | null | undefined,
) => {
  const storeInstance = useWorkflowStore.getState();
  const currentState = storeInstance.workflow?.nodes[nodeId]?.state;
  if (state == null) {
    if (!currentState) {
      return;
    }
    const currentPriority = getStagePriority(currentState.stage);
    if (currentPriority > 0) {
      return;
    }
    return;
  }
  const updates: WorkflowNodeStateUpdateMap = { [nodeId]: state };
  updateWorkflowDefinitionNodeStates(queryClient, runId, updates);
};

export const updateRunDefinitionNodeRuntime = (
  queryClient: QueryClient,
  runId: string,
  nodeId: string,
  runtime: WorkflowNodeRuntimeUpdate,
) => {
  updateWorkflowDefinitionNodeRuntime(queryClient, runId, {
    [nodeId]: runtime,
  });
};

export const applyRunDefinitionSnapshot = (
  queryClient: QueryClient,
  runId: string,
  nodes: RunNodeStatus[] | null | undefined,
) => {
  if (!nodes?.length) {
    return;
  }
  const storeInstance = useWorkflowStore.getState();
  const stateUpdates: WorkflowNodeStateUpdateMap = {};
  nodes.forEach((node) => {
    const nextState = (node.state as WorkflowNodeState | undefined) ?? undefined;
    if (!nextState) {
      return;
    }
    const nextStage = nextState.stage;
    const currentState = storeInstance.workflow?.nodes[node.nodeId]?.state;
    if (currentState) {
      const currentStage = currentState.stage;
      const currentPriority = getStagePriority(currentStage);
      const nextPriority = getStagePriority(nextStage);
      if (currentPriority > 0 && nextPriority === 0) {
        return;
      }
      if (nextPriority < currentPriority) {
        return;
      }
    }
    stateUpdates[node.nodeId] = nextState;
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
    return acc;
  }, {});

  if (Object.keys(stateUpdates).length) {
    updateWorkflowDefinitionNodeStates(queryClient, runId, stateUpdates);
  }
  if (Object.keys(runtimeUpdates).length) {
    updateWorkflowDefinitionNodeRuntime(queryClient, runId, runtimeUpdates);
  }
};





