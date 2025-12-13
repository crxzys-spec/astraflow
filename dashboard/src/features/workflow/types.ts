import type {
  ManifestNode,
  NodeUI,
  UIPort,
  UIWidget,
  WorkflowSubgraph,
  RunArtifact,
  Workflow as ApiWorkflow,
  WorkflowEdge as ApiWorkflowEdge,
  WorkflowMetadata as ApiWorkflowMetadata,
  WorkflowNode as ApiWorkflowNode,
  WorkflowNodeSchema as ApiWorkflowNodeSchema,
  WorkflowNodeState as ApiWorkflowNodeState,
  WorkflowSubgraphMetadata as ApiWorkflowSubgraphMetadata,
} from '../../client/models';

export type WorkflowDefinition = ApiWorkflow;
export type WorkflowDefinitionNode = ApiWorkflowNode;
export type WorkflowDefinitionEdge = ApiWorkflowEdge;
export type WorkflowMetadata = ApiWorkflowMetadata;
export type WorkflowNodeSchema = ApiWorkflowNodeSchema;
export type WorkflowSubgraphMetadata = ApiWorkflowSubgraphMetadata;
export type WorkflowNodeState = ApiWorkflowNodeState;
export type ManifestNodeTemplate = ManifestNode;
export type RunArtifactModel = RunArtifact;

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
  runtimeArtifacts?: RunArtifactModel[] | null;
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
  runtimeArtifacts?: RunArtifactModel[] | null;

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
  selectedNodeIds: string[];
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

  updateWorkflowMetadata: (changes: Partial<WorkflowMetadata>) => void;
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

      artifacts?: RunArtifactModel[] | null;

      summary?: string | null;

    }

  ) => void;

  resetRunState: () => void;
  setActiveGraph: (scope: WorkflowGraphScope, options?: { recordHistory?: boolean }) => void;
  setSelectedNodes: (nodeIds: string[]) => void;
  toggleSelectedNode: (nodeId: string) => void;
  setNodePosition: (nodeId: string, position: XYPosition, options?: { record?: boolean }) => void;
  setNodePositions: (positions: Record<string, XYPosition>, options?: { record?: boolean }) => void;
  captureHistory: () => void;
  undo: () => void;
  redo: () => void;
  canUndo: () => boolean;
  canRedo: () => boolean;
  inlineSubgraphIntoActiveGraph: (containerNodeId?: string, subgraphId?: string) => InlineSubgraphResult;
  convertSelectionToSubgraph: (containerTemplate?: WorkflowPaletteNode) => ConvertSelectionResult;
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
  | { type: "root"; subgraphId?: string }
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
  selectedNodeIds: string[];
  activeGraph: WorkflowGraphScope;
}

export interface InlineSubgraphResult {
  ok: boolean;
  error?: string;
}

export interface ConvertSelectionResult {
  ok: boolean;
  error?: string;
  subgraphId?: string;
  containerId?: string;
}


