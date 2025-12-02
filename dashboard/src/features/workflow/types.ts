import type { ManifestNode } from '../../api/models/manifestNode';
import type { Workflow as ApiWorkflow } from '../../api/models/workflow';
import type { WorkflowEdge as ApiWorkflowEdge } from '../../api/models/workflowEdge';
import type { WorkflowMetadata } from '../../api/models/workflowMetadata';
import type { WorkflowNode as ApiWorkflowNode } from '../../api/models/workflowNode';
import type { WorkflowNodeSchema } from '../../api/models/workflowNodeSchema';
import type { RunArtifact } from '../../api/models/runArtifact';
import type { NodeUI } from '../../api/models/nodeUI';
import type { UIPort } from '../../api/models/uIPort';
import type { UIWidget } from '../../api/models/uIWidget';
import type { WorkflowNodeState } from '../../api/models/workflowNodeState';
import type { WorkflowSubgraph } from '../../api/models/workflowSubgraph';
import type { WorkflowSubgraphMetadata } from '../../api/models/workflowSubgraphMetadata';
export type WorkflowDefinition = ApiWorkflow;
export type WorkflowDefinitionNode = ApiWorkflowNode;
export type WorkflowDefinitionEdge = ApiWorkflowEdge;
export type ManifestNodeTemplate = ManifestNode;

export interface WorkflowDraft {
  id: string;
  schemaVersion: string;
  metadata?: WorkflowMetadata;
  tags?: string[];
  previewImage?: string | null;
  nodes: Record<string, WorkflowNodeDraft>;
  edges: WorkflowEdgeDraft[];
  subgraphs?: WorkflowSubgraphDraft[];
  dirty: boolean;
}

export interface WorkflowMiddlewareDraft {
  id: string;
  label: string;
  role?: "middleware";
  nodeKind: string;
  status?: string;
  category?: string;
  description?: string;
  tags?: string[];
  packageName?: string;
  packageVersion?: string;
  adapter?: string;
  handler?: string;
  parameters: Record<string, unknown>;
  results: Record<string, unknown>;
  schema?: WorkflowNodeSchema;
  ui?: NodeUI;
  resources?: WorkflowResourceBinding[];
  affinity?: Record<string, unknown>;
  concurrencyKey?: string;
  metadata?: Record<string, unknown>;
  state?: WorkflowNodeState;
  runtimeArtifacts?: RunArtifact[] | null;
  runtimeSummary?: string | null;
}

export interface WorkflowNodeDraft {
  id: string;
  label: string;
  role?: "node" | "container" | "middleware";
  nodeKind: string;
  status?: string;
  category?: string;
  description?: string;
  tags?: string[];
  packageName?: string;
  packageVersion?: string;
  adapter?: string;
  handler?: string;
  parameters: Record<string, unknown>;
  results: Record<string, unknown>;
  schema?: WorkflowNodeSchema;
  ui?: NodeUI;
  position: XYPosition;
  dependencies: string[];
  middlewares?: WorkflowMiddlewareDraft[];
  resources?: WorkflowResourceBinding[];
  affinity?: Record<string, unknown>;
  concurrencyKey?: string;
  metadata?: Record<string, unknown>;
  state?: WorkflowNodeState;
  runtimeArtifacts?: RunArtifact[] | null;
  runtimeSummary?: string | null;
}

export interface WorkflowEdgeDraft {
  id: string;
  source: WorkflowEdgeEndpointDraft;
  target: WorkflowEdgeEndpointDraft;
  metadata?: Record<string, unknown>;
}

export interface WorkflowEdgeEndpointDraft {
  nodeId: string;
  portId: string;
}

export interface WorkflowResourceBinding {
  id: string;
  type?: string;
  path?: string;
  mode?: string;
  metadata?: Record<string, unknown>;
}

export interface XYPosition {
  x: number;
  y: number;
}

export interface WorkflowPaletteNode {
  template: ManifestNodeTemplate;
  packageName?: string;
  packageVersion?: string;
}

export type WorkflowNodeStore = Record<string, WorkflowNodeDraft>;

export interface WorkflowStoreState {
  workflow?: WorkflowDraft;
  selectedNodeId?: string;
  subgraphDrafts: WorkflowSubgraphDraftEntry[];
  activeGraph: WorkflowGraphScope;
  history: {
    past: WorkflowHistoryEntry[];
    future: WorkflowHistoryEntry[];
  };
}

export type WorkflowNodeStateUpdateMap = Record<string, WorkflowNodeState | null | undefined>;

export interface WorkflowStoreActions {
  loadWorkflow: (definition: WorkflowDefinition) => void;
  resetWorkflow: () => void;
  setPreviewImage: (preview?: string | null) => void;
  addNodeFromTemplate: (
    template: WorkflowPaletteNode,
    position: XYPosition
  ) => WorkflowNodeDraft;
  updateNode: (
    nodeId: string,
    updater: (node: WorkflowNodeDraft) => WorkflowNodeDraft
  ) => void;
  removeNode: (nodeId: string) => void;
  setSelectedNode: (nodeId?: string) => void;
  addEdge: (edge: WorkflowEdgeDraft) => void;
  updateEdge: (
    edgeId: string,
    updater: (edge: WorkflowEdgeDraft) => WorkflowEdgeDraft
  ) => void;
  removeEdge: (edgeId: string) => void;
  markDirty: () => void;
  updateNodeStates: (updates: WorkflowNodeStateUpdateMap) => void;
  updateNodeRuntime: (
    nodeId: string,
    payload: {
      result?: Record<string, unknown> | null;
      artifacts?: RunArtifact[] | null;
      summary?: string | null;
    }
  ) => void;
  resetRunState: () => void;
  setActiveGraph: (scope: WorkflowGraphScope) => void;
  undo: () => void;
  redo: () => void;
  canUndo: () => boolean;
  canRedo: () => boolean;
}

export type WorkflowStore = WorkflowStoreState & WorkflowStoreActions;

export type NodeWidgetDefinition = UIWidget;
export type NodePortDefinition = UIPort;

export type WorkflowSubgraphDraft = WorkflowSubgraph;

export interface WorkflowSubgraphDraftEntry {
  id: string;
  definition: WorkflowDraft;
  metadata?: WorkflowSubgraphMetadata;
}

export type WorkflowGraphScope =
  | { type: "root" }
  | { type: "subgraph"; subgraphId: string };

export interface ContainerSettings {
  subgraphId?: string;
  timeoutSeconds?: number | null;
  notes?: string | null;
}

export interface WorkflowHistoryEntry {
  workflow?: WorkflowDraft;
  subgraphDrafts: WorkflowSubgraphDraftEntry[];
  selectedNodeId?: string;
  activeGraph: WorkflowGraphScope;
}





