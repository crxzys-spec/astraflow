import type { Edge, Node } from "reactflow";
import type { WorkflowDraft } from "../types.ts";

export const buildFlowNodes = (workflow: WorkflowDraft, selectedNodeId?: string): Node[] => {
  const fallbackInputPorts: Record<string, Set<string>> = {};
  const fallbackOutputPorts: Record<string, Set<string>> = {};

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

  return Object.values(workflow.nodes).map((node) => ({
    id: node.id,
    type: "workflow",
    position: { ...node.position },
    selected: node.id === selectedNodeId,
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
      fallbackOutputPorts: Array.from(fallbackOutputPorts[node.id] ?? [])
    }
  }));
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




