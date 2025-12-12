import type { QueryClient } from "@tanstack/react-query";
import type { NodeResultDeltaEvent } from "../../api/models/nodeResultDeltaEvent";
import type { Run } from "../../api/models/run";
import type { RunList } from "../../api/models/runList";
import type { RunNodeStatus } from "../../api/models/runNodeStatus";
import type { RunRef } from "../../api/models/runRef";
import { getGetRunQueryKey } from "../../api/endpoints";
import { applyResultDelta } from "../utils/jsonDelta";

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
  queryClient.setQueryData<Run>(runKey, normalizedRun);

  const matchingLists = queryClient.getQueriesData<RunList>({
    queryKey: [RUNS_QUERY_PREFIX],
  });

  matchingLists.forEach(([queryKey, response]) => {
    const items = response?.items ?? [];
    const index = items.findIndex((item) => item.runId === run.runId);
    const nextItems =
      index === -1
        ? [normalizedRun, ...items]
        : items.map((item, idx) => (idx === index ? { ...item, ...normalizedRun } : item));
    queryClient.setQueryData<RunList>(queryKey, {
      ...(response ?? { items: [] }),
      items: nextItems,
    });
  });
};

export const updateRunCaches = (
  queryClient: QueryClient,
  runId: string,
  mutator: RunMutator,
) => {
  const runKey = getGetRunQueryKey(runId);
  queryClient.setQueryData<Run | undefined>(runKey, (existing) => {
    if (!existing) {
      return existing;
    }
    const updatedRun = applyMutator(existing, mutator);
    if (updatedRun === existing) {
      return existing;
    }
    return updatedRun;
  });

  const matchingLists = queryClient.getQueriesData<RunList>({
    queryKey: [RUNS_QUERY_PREFIX],
  });

  matchingLists.forEach(([queryKey, response]) => {
    const items = response?.items ?? [];
    if (!items.length) {
      return;
    }
    const index = items.findIndex((item) => item.runId === runId);
    if (index === -1) {
      return;
    }
    const candidate = items[index];
    const updatedRun = applyMutator(candidate, mutator);
    if (updatedRun === candidate) {
      return;
    }
    const nextItems = items.slice();
    nextItems[index] = updatedRun;
    queryClient.setQueryData<RunList>(queryKey, {
      ...response,
      items: nextItems,
    });
  });
};

export const replaceRunSnapshot = (
  queryClient: QueryClient,
  runId: string,
  snapshot: Run,
  nodes?: RunNodeStatus[] | null,
) => {
  const applySnapshot = (existing?: Run | null): Run => {
    const nextNodes = nodes ?? snapshot.nodes ?? existing?.nodes;
    return {
      ...(existing ?? snapshot),
      ...snapshot,
      runId,
      nodes: nextNodes,
    };
  };

  const runKey = getGetRunQueryKey(runId);
  const currentRun = queryClient.getQueryData<Run | undefined>(runKey) ?? null;
  const mergedRun = applySnapshot(currentRun);
  queryClient.setQueryData<Run>(runKey, mergedRun);

  const matchingLists = queryClient.getQueriesData<RunList>({
    queryKey: [RUNS_QUERY_PREFIX],
  });

  matchingLists.forEach(([queryKey, response]) => {
    const items = response?.items ?? [];
    const index = items.findIndex((item) => item.runId === runId);
    const nextItems =
      index === -1
        ? [mergedRun, ...items]
        : items.map((item, idx) => (idx === index ? applySnapshot(item) : item));

    queryClient.setQueryData<RunList>(queryKey, {
      ...(response ?? { items: [] }),
      items: nextItems,
    });
  });
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

export const updateRunNodeResultDelta = (
  queryClient: QueryClient,
  runId: string,
  nodeId: string,
  delta: Pick<NodeResultDeltaEvent, "operation" | "path" | "payload" | "patches" | "nodeId">,
) => {
  const runKey = getGetRunQueryKey(runId);
  queryClient.setQueryData<Run | undefined>(runKey, (existing) => {
    const run = existing;
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
      ...run,
      nodes: nextNodes,
    };
  });
};
