import type { QueryClient } from "@tanstack/react-query";
import type { AxiosResponse } from "axios";

import type { Run } from "../api/models/run";
import type { WorkflowNodeState } from "../api/models/workflowNodeState";
import type { RunArtifact } from "../api/models/runArtifact";
import type { RunList } from "../api/models/runList";
import type { RunNodeStatus } from "../api/models/runNodeStatus";
import type { StartRunRequestWorkflow } from "../api/models/startRunRequestWorkflow";
import { getGetRunDefinitionQueryKey, getGetRunQueryKey } from "../api/endpoints";
import { useWorkflowStore } from "../features/workflow";
import type { WorkflowNodeStateUpdateMap } from "../features/workflow";

const RUNS_QUERY_PREFIX = "/api/v1/runs";

type RunMutator = (run: Run) => Run;

const applyMutator = (run: Run, mutator: RunMutator): Run => {
  const next = mutator(run);
  return next === run ? run : { ...next };
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

const cloneRuntimeResult = (
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
  queryClient.setQueryData<AxiosResponse<StartRunRequestWorkflow>>(definitionKey, (existing) => {
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
  queryClient.setQueryData<AxiosResponse<StartRunRequestWorkflow>>(definitionKey, (existing) => {
    if (!existing?.data?.nodes?.length) {
      return existing;
    }
    let changed = false;
    const nextNodes = existing.data.nodes.map((node) => {
      const update = updates[node.id];
      if (!update) {
        return node;
      }
      const currentResult =
        (node as unknown as { runtimeResult?: Record<string, unknown> | null }).runtimeResult;
      const currentArtifacts =
        (node as unknown as { runtimeArtifacts?: RunArtifact[] | null }).runtimeArtifacts;
      const currentSummary =
        (node as unknown as { runtimeSummary?: string | null }).runtimeSummary;

      const nextResult = cloneRuntimeResult(update.result);
      const nextArtifacts = cloneRuntimeArtifacts(update.artifacts);
      const nextSummary = update.summary !== undefined ? update.summary ?? null : currentSummary;

      const willUpdateResult =
        update.result !== undefined && !valuesEqual(currentResult ?? undefined, nextResult);
      const willUpdateArtifacts =
        update.artifacts !== undefined && !valuesEqual(currentArtifacts ?? undefined, nextArtifacts);
      const willUpdateSummary =
        update.summary !== undefined && !valuesEqual(currentSummary ?? undefined, nextSummary);

      if (!willUpdateResult && !willUpdateArtifacts && !willUpdateSummary) {
        return node;
      }

      const nodeUpdate: WorkflowNodeRuntimeUpdate = {};
      if (willUpdateResult) {
        nodeUpdate.result = nextResult ?? null;
      }
      if (willUpdateArtifacts) {
        nodeUpdate.artifacts = nextArtifacts ?? null;
      }
      if (willUpdateSummary) {
        nodeUpdate.summary = nextSummary ?? null;
      }
      effectiveUpdates[node.id] = nodeUpdate;
      changed = true;

      return {
        ...node,
        runtimeResult: willUpdateResult ? nextResult ?? null : currentResult,
        runtimeArtifacts: willUpdateArtifacts ? nextArtifacts ?? null : currentArtifacts,
        runtimeSummary: willUpdateSummary ? nextSummary ?? null : currentSummary,
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
  let storePayload: Record<string, WorkflowNodeRuntimeUpdate> = effectiveUpdates;
  if (
    Object.keys(storePayload).length === 0 &&
    storeInstance.workflow &&
    Object.keys(updates).length
  ) {
    const fallback: Record<string, WorkflowNodeRuntimeUpdate> = {};
    Object.entries(updates).forEach(([nodeId, update]) => {
      const node = storeInstance.workflow?.nodes[nodeId];
      if (!node) {
        return;
      }
      const candidate: WorkflowNodeRuntimeUpdate = {};
      if (update.result !== undefined) {
        const nextResult = cloneRuntimeResult(update.result);
        if (!valuesEqual(node.runtimeResult ?? undefined, nextResult)) {
          candidate.result = nextResult ?? null;
        }
      }
      if (update.artifacts !== undefined) {
        const nextArtifacts = cloneRuntimeArtifacts(update.artifacts);
        if (!valuesEqual(node.runtimeArtifacts ?? undefined, nextArtifacts)) {
          candidate.artifacts = nextArtifacts ?? null;
        }
      }
      if (update.summary !== undefined) {
        const nextSummary = update.summary ?? null;
        if (!valuesEqual(node.runtimeSummary ?? undefined, nextSummary)) {
          candidate.summary = nextSummary;
        }
      }
      if (Object.keys(candidate).length > 0) {
        fallback[nodeId] = candidate;
      }
    });
    storePayload = fallback;
  }
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





