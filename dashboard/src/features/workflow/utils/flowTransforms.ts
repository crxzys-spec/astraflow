import type { Edge, Node } from "reactflow";
import type { WorkflowDraft } from "../types.ts";

export const buildFlowNodes = (workflow: WorkflowDraft): Node[] =>
  Object.values(workflow.nodes).map((node) => ({
    id: node.id,
    type: "default",
    position: { ...node.position },
    data: {
      nodeId: node.id,
      label: node.label,
      status: (node.results?.status as string | undefined) ?? undefined,
      packageName: node.packageName,
      packageVersion: node.packageVersion
    }
  }));

export const buildFlowEdges = (workflow: WorkflowDraft): Edge[] =>
  workflow.edges.map((edge) => ({
    id: edge.id,
    source: edge.source.nodeId,
    target: edge.target.nodeId,
    sourceHandle: edge.source.portId,
    targetHandle: edge.target.portId,
    data: edge.metadata
  }));

