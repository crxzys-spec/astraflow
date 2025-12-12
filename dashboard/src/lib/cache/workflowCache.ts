import type { QueryClient } from "@tanstack/react-query";
import type { NodeResultDeltaEvent } from "../../api/models/nodeResultDeltaEvent";
import type { RunArtifact } from "../../api/models/runArtifact";
import type { RunNodeStatus } from "../../api/models/runNodeStatus";
import type { Workflow } from "../../api/models/workflow";
import type { WorkflowNodeState } from "../../api/models/workflowNodeState";
import { getGetRunDefinitionQueryKey } from "../../api/endpoints";
import { useWorkflowStore } from "../../features/workflow";
import type { WorkflowNodeStateUpdateMap } from "../../features/workflow";
import { applyResultDelta, valuesEqual } from "../utils/jsonDelta";
import { cloneResultRecord, cloneRuntimeArtifacts, cloneWorkflowState } from "./cacheUtils";

type WorkflowNodeRuntimeUpdate = {
  result?: Record<string, unknown> | null;
  artifacts?: RunArtifact[] | null;
  summary?: string | null;
};

type RuntimeMiddleware = {
  id?: string;
  state?: WorkflowNodeState;
  result?: unknown;
  artifacts?: unknown;
  metadata?: { summary?: string | null };
};

const findDraftNode = (
  nodeId: string,
  store: ReturnType<typeof useWorkflowStore.getState> | null,
): unknown => {
  if (!store) {
    return undefined;
  }
  const searchWorkflow = (workflow?: { nodes?: Record<string, unknown> }) => {
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
  queryClient.setQueryData<Workflow | undefined>(definitionKey, (existing) => {
    if (!existing?.nodes?.length) {
      return existing;
    }
    let changed = false;
    const nextNodes = existing.nodes.map((node) => {
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
      nodes: nextNodes,
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

  queryClient.setQueryData<Workflow | undefined>(definitionKey, (existing) => {
    if (!existing) {
      return existing;
    }
    const result = applyRuntimeUpdatesToWorkflow(existing);
    if (!result.changed) {
      return existing;
    }
    return result.workflow;
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

  const definition = queryClient.getQueryData<Workflow | undefined>(definitionKey);
  const findResultInWorkflow = (
    workflow?: Workflow,
  ): Record<string, unknown> | null | undefined => {
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
  fallback?: string | null,
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
  nodeId: string,
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
      const castNode = node as {
        id?: string;
        state?: WorkflowNodeState;
        middlewares?: { id: string; state?: WorkflowNodeState }[];
      };
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

    const middlewares = (node as { middlewares?: { id?: string; state?: WorkflowNodeState }[] })
      .middlewares;
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

    const middlewares = (node as { middlewares?: RuntimeMiddleware[] }).middlewares;
    middlewares?.forEach((mw) => {
      const mwId = mw.id;
      if (!mwId) {
        return;
      }
      const mwPayload: WorkflowNodeRuntimeUpdate = {};
      if (mw.result !== undefined) {
        mwPayload.result = (mw.result as Record<string, unknown> | null) ?? null;
      }
      if (mw.artifacts !== undefined) {
        mwPayload.artifacts = mw.artifacts ?? null;
      }
      const mwSummary = mw.metadata?.summary;
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
