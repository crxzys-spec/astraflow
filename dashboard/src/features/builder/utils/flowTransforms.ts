import type { Edge, Node } from "reactflow";
import type { WorkflowDraft, WorkflowMiddlewareDraft } from "../types.ts";

export const buildFlowNodes = (workflow: WorkflowDraft, selectedNodeIds: string[] = []): Node[] => {
  const fallbackInputPorts: Record<string, Set<string>> = {};
  const fallbackOutputPorts: Record<string, Set<string>> = {};
  const attachedByHost: Record<
    string,
    { id: string; label: string; node: WorkflowMiddlewareDraft; index: number }[]
  > = {};

  workflow.edges.forEach((edge) => {
    if (edge.source.portId) {
      const existing = fallbackOutputPorts[edge.source.nodeId] ?? new Set<string>();
      existing.add(edge.source.portId);
      fallbackOutputPorts[edge.source.nodeId] = existing;
    }
    if (edge.target.portId) {
      const existing = fallbackInputPorts[edge.target.nodeId] ?? new Set<string>();
      existing.add(edge.target.portId);
      fallbackInputPorts[edge.target.nodeId] = existing;
    }
  });

  Object.values(workflow.nodes).forEach((node) => {
    (node.middlewares ?? []).forEach((middleware, index) => {
      const list = attachedByHost[node.id] ?? [];
      list.push({ id: middleware.id, label: middleware.label ?? middleware.id, node: middleware, index });
      attachedByHost[node.id] = list;
    });
  });

  return Object.values(workflow.nodes)
    .filter((node) => node.role !== "middleware")
    .map((node) => {
    const basePos = { x: node.position.x ?? 0, y: node.position.y ?? 0 };

    return {
      id: node.id,
      type: "workflow",
      position: basePos,
      draggable: true,
      selected: selectedNodeIds.includes(node.id),
      data: {
        nodeId: node.id,
        label: node.label,
        status: node.status,
        stage: node.state?.stage,
        progress: typeof node.state?.progress === "number" ? node.state.progress : undefined,
        message: typeof node.state?.message === "string" ? node.state.message : undefined,
        lastUpdatedAt: node.state?.lastUpdatedAt,
        packageName: node.packageName,
        packageVersion: node.packageVersion,
        adapter: node.adapter,
        handler: node.handler,
        widgets: node.ui?.widgets ?? [],
        fallbackInputPorts: Array.from(fallbackInputPorts[node.id] ?? []),
        fallbackOutputPorts: Array.from(fallbackOutputPorts[node.id] ?? []),
        middlewares: node.middlewares ?? [],
        attachedMiddlewares: attachedByHost[node.id] ?? [],
        role: node.role,
      },
    };
  });
};

export const buildFlowEdges = (workflow: WorkflowDraft): Edge[] =>
  workflow.edges.map((edge) => ({
    id: edge.id,
    source: edge.source.nodeId,
    target: edge.target.nodeId,
    sourceHandle: edge.source.portId,
    targetHandle: edge.target.portId,
    data: edge.metadata
  }));




