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

export type WorkflowDefinition = ApiWorkflow;
export type WorkflowDefinitionNode = ApiWorkflowNode;
export type WorkflowDefinitionEdge = ApiWorkflowEdge;
export type ManifestNodeTemplate = ManifestNode;

export interface WorkflowDraft {
  id: string;
  schemaVersion: string;
  metadata?: WorkflowMetadata;
  tags?: string[];
  nodes: Record<string, WorkflowNodeDraft>;
  edges: WorkflowEdgeDraft[];
  dirty: boolean;
}

export interface WorkflowNodeDraft {
  id: string;
  label: string;
  nodeKind: string;
  status?: string;
  category?: string;
  description?: string;
  tags?: string[];
  packageName?: string;
  packageVersion?: string;
  parameters: Record<string, unknown>;
  results: Record<string, unknown>;
  schema?: WorkflowNodeSchema;
  ui?: NodeUI;
  position: XYPosition;
  dependencies: string[];
  resources?: WorkflowResourceBinding[];
  affinity?: Record<string, unknown>;
  concurrencyKey?: string;
  metadata?: Record<string, unknown>;
  state?: WorkflowNodeState;
  runtimeResult?: Record<string, unknown> | null;
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
}

export type WorkflowNodeStateUpdateMap = Record<string, WorkflowNodeState | null | undefined>;

export interface WorkflowStoreActions {
  loadWorkflow: (definition: WorkflowDefinition) => void;
  resetWorkflow: () => void;
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
}

export type WorkflowStore = WorkflowStoreState & WorkflowStoreActions;

export type NodeWidgetDefinition = UIWidget;
export type NodePortDefinition = UIPort;







