import { useMemo } from "react";
import type { RunNodeStatusMetadata } from "../client/model-shims";
import type { RunModel, RunNodeStatusModel } from "../services/runs";
import type { Workflow, WorkflowMiddleware } from "../client/models";
import { buildMiddlewareTraces } from "../lib/middlewareTrace";

export type FrameMetadata = {
  frameId?: string;
  containerNodeId?: string;
  subgraphId?: string;
  subgraphName?: string;
  aliasChain?: string[];
};

export type NodeWithFrame = {
  node: RunNodeStatusModel;
  frame?: FrameMetadata;
};

export type MiddlewareRelations = {
  roleByNode: Record<string, string | undefined>;
  chainByHost: Record<string, WorkflowMiddleware[]>;
  hostByMiddleware: Record<string, string>;
};

export type NodeGroup = {
  key: string;
  label: string;
  description?: string;
  nodes: NodeWithFrame[];
};

export const parseFrameMetadata = (
  metadata: RunNodeStatusMetadata | undefined | null,
): FrameMetadata | undefined => {
  if (!metadata || typeof metadata !== "object") {
    return undefined;
  }
  const frame = (metadata as Record<string, unknown>)["__frame"];
  if (!frame || typeof frame !== "object") {
    return undefined;
  }
  const source = frame as Record<string, unknown>;
  const aliasSource = source["aliasChain"];
  const aliasChain = Array.isArray(aliasSource)
    ? aliasSource.filter((entry): entry is string => typeof entry === "string")
    : undefined;
  return {
    frameId: typeof source["frameId"] === "string" ? (source["frameId"] as string) : undefined,
    containerNodeId:
      typeof source["containerNodeId"] === "string"
        ? (source["containerNodeId"] as string)
        : undefined,
    subgraphId:
      typeof source["subgraphId"] === "string" ? (source["subgraphId"] as string) : undefined,
    subgraphName:
      typeof source["subgraphName"] === "string"
        ? (source["subgraphName"] as string)
        : undefined,
    aliasChain,
  };
};

export const deriveMiddlewareRelations = (
  workflowDefinition?: Pick<Workflow, "nodes"> | null,
): MiddlewareRelations => {
  const roleByNode: Record<string, string | undefined> = {};
  const chainByHost: Record<string, WorkflowMiddleware[]> = {};
  const hostByMiddleware: Record<string, string> = {};
  const nodes = workflowDefinition?.nodes ?? [];
  nodes.forEach((definitionNode) => {
    roleByNode[definitionNode.id ?? ""] = (definitionNode as { role?: string }).role;
    const middlewares =
      (definitionNode as { middlewares?: WorkflowMiddleware[] }).middlewares ?? [];
    if (middlewares?.length) {
      chainByHost[definitionNode.id ?? ""] = middlewares;
      middlewares.forEach((mw) => {
        if (mw.id) {
          hostByMiddleware[mw.id] = definitionNode.id ?? "";
        }
      });
    }
  });
  return { roleByNode, chainByHost, hostByMiddleware };
};

export const mapNodesWithFrame = (nodes?: RunNodeStatusModel[] | null): NodeWithFrame[] => {
  if (!nodes?.length) {
    return [];
  }
  return nodes.map((node) => ({
    node,
    frame: parseFrameMetadata(node.metadata),
  }));
};

export const filterNodesWithFrame = (
  nodesWithFrame: NodeWithFrame[],
  middlewareRelations: MiddlewareRelations,
  showMiddlewareOnly: boolean,
): NodeWithFrame[] => {
  if (!showMiddlewareOnly) {
    return nodesWithFrame;
  }
  return nodesWithFrame.filter(
    (entry) =>
      middlewareRelations.chainByHost[entry.node.nodeId]?.length ||
      Boolean(middlewareRelations.hostByMiddleware[entry.node.nodeId]),
  );
};

export const groupNodesByFrame = (nodes: NodeWithFrame[]): NodeGroup[] => {
  if (!nodes.length) {
    return [];
  }
  const groups: NodeGroup[] = [];
  const rootNodes = nodes.filter((entry) => !entry.frame);
  if (rootNodes.length) {
    groups.push({
      key: "main",
      label: "Main Graph",
      nodes: rootNodes,
    });
  }
  const subgraphMap = new Map<string, NodeGroup>();
  nodes.forEach((entry) => {
    const frame = entry.frame;
    if (!frame) {
      return;
    }
    const aliasKey = frame.aliasChain?.join("::");
    const fallbackKey = [frame.containerNodeId, frame.subgraphId].filter(Boolean).join("::");
    const mapKey =
      frame.frameId ??
      aliasKey ??
      (fallbackKey.length > 0 ? fallbackKey : `subgraph-${subgraphMap.size + 1}`);
    const baseLabel =
      frame.subgraphName ??
      frame.subgraphId ??
      frame.frameId ??
      frame.containerNodeId ??
      "Subgraph";
    const description =
      frame.aliasChain && frame.aliasChain.length > 1
        ? frame.aliasChain.join(" / ")
        : frame.aliasChain?.[0];
    const existing = subgraphMap.get(mapKey);
    if (existing) {
      existing.nodes.push(entry);
      if (!existing.description && description) {
        existing.description = description;
      }
      return;
    }
    subgraphMap.set(mapKey, {
      key: mapKey,
      label: `Subgraph: ${baseLabel}`,
      description,
      nodes: [entry],
    });
  });
  const orderedSubgraphs = Array.from(subgraphMap.values()).sort((a, b) =>
    a.label.localeCompare(b.label),
  );
  groups.push(...orderedSubgraphs);
  return groups;
};

export const useRunDetailData = ({
  runData,
  workflowDefinition,
  showMiddlewareOnly,
}: {
  runData?: RunModel | null;
  workflowDefinition?: Workflow | null;
  showMiddlewareOnly: boolean;
}) => {
  const middlewareRelations = useMemo(
    () => deriveMiddlewareRelations(workflowDefinition),
    [workflowDefinition],
  );
  const nodesWithFrame = useMemo(
    () => mapNodesWithFrame(runData?.nodes),
    [runData?.nodes],
  );
  const middlewareTraces = useMemo(
    () => buildMiddlewareTraces(runData?.nodes),
    [runData?.nodes],
  );
  const filteredNodesWithFrame = useMemo(
    () => filterNodesWithFrame(nodesWithFrame, middlewareRelations, showMiddlewareOnly),
    [middlewareRelations, nodesWithFrame, showMiddlewareOnly],
  );
  const nodeGroups = useMemo(
    () => groupNodesByFrame(filteredNodesWithFrame),
    [filteredNodesWithFrame],
  );

  return {
    middlewareRelations,
    nodesWithFrame,
    filteredNodesWithFrame,
    nodeGroups,
    middlewareTraces,
  };
};

