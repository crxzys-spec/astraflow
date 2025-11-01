import { nanoid } from 'nanoid';
import type { EdgeEndpoint } from '../../../api/models/edgeEndpoint';
import type { Workflow as WorkflowDefinition } from '../../../api/models/workflow';
import type { WorkflowEdge } from '../../../api/models/workflowEdge';
import type { WorkflowNode } from '../../../api/models/workflowNode';
import type { WorkflowNodeSchema } from '../../../api/models/workflowNodeSchema';
import type {
  WorkflowDraft,
  WorkflowEdgeDraft,
  WorkflowEdgeEndpointDraft,
  WorkflowNodeDraft,
  WorkflowPaletteNode,
  XYPosition
} from '../types.ts';
import { buildDefaultsFromSchema } from './schemaDefaults.ts';
import type { JsonSchema } from './schemaDefaults.ts';

const clone = <T>(value: T): T => (value === undefined ? value : (JSON.parse(JSON.stringify(value)) as T));

const nodeDefaultsFromSchema = (schema?: WorkflowNodeSchema | Record<string, unknown> | null) => {
  const container = (schema ?? {}) as { parameters?: JsonSchema; results?: JsonSchema };
  const parametersSchema = container.parameters as JsonSchema | undefined;
  const resultsSchema = container.results as JsonSchema | undefined;
  return {
    parameters: parametersSchema ? buildDefaultsFromSchema(parametersSchema) : {},
    results: resultsSchema ? buildDefaultsFromSchema(resultsSchema) : {}
  };
};

const mapEdgeToDraft = (edge: WorkflowEdge): WorkflowEdgeDraft => ({
  id: edge.id ?? nanoid(),
  source: mapEndpoint(edge.source),
  target: mapEndpoint(edge.target)
});

const mapEndpoint = (endpoint: EdgeEndpoint): WorkflowEdgeEndpointDraft => ({
  nodeId: endpoint.node,
  portId: endpoint.port
});

export const workflowDefinitionToDraft = (definition: WorkflowDefinition): WorkflowDraft => {
  const nodes: Record<string, WorkflowNodeDraft> = {};

  definition.nodes.forEach((node: WorkflowNode) => {
    const { parameters: defaultParams, results: defaultResults } = nodeDefaultsFromSchema(node.schema);
    const draft: WorkflowNodeDraft = {
      id: node.id,
      label: node.label,
      nodeKind: node.type,
    status: node.status ?? "draft",
    category: node.category ?? "uncategorised",
    description: node.description,
    tags: node.tags,
    packageName: node.package?.name,
    packageVersion: node.package?.version,
      parameters: clone(node.parameters ?? defaultParams),
      results: clone(node.results ?? defaultResults),
      schema: node.schema,
      ui: node.ui,
      position: {
        x: node.position?.x ?? 0,
        y: node.position?.y ?? 0
      },
      dependencies: [],
      resources: []
    };
    nodes[draft.id] = draft;
  });

  const edges: WorkflowEdgeDraft[] = (definition.edges ?? []).map(mapEdgeToDraft);

  // populate dependencies
  edges.forEach((edge) => {
    const target = nodes[edge.target.nodeId];
    if (target && !target.dependencies.includes(edge.source.nodeId)) {
      target.dependencies.push(edge.source.nodeId);
    }
  });

  return {
    id: definition.id,
    schemaVersion: definition.schemaVersion,
    metadata: definition.metadata,
    tags: definition.tags,
    nodes,
    edges,
    dirty: false
  };
};

export const workflowDraftToDefinition = (draft: WorkflowDraft): WorkflowDefinition => {
  const nodes: WorkflowNode[] = Object.values(draft.nodes).map((node) => ({
    id: node.id,
    type: node.nodeKind,
    package: {
      name: node.packageName ?? '',
      version: node.packageVersion ?? ''
    },
    status: node.status ?? "draft",
    category: node.category ?? "uncategorised",
    label: node.label,
    description: node.description,
    tags: node.tags,
    position: { x: node.position.x, y: node.position.y },
    parameters: clone(node.parameters),
    results: clone(node.results),
    schema: node.schema,
    ui: node.ui
  }));

  const edges: WorkflowEdge[] = draft.edges.map((edge) => ({
    id: edge.id,
    source: { node: edge.source.nodeId, port: edge.source.portId },
    target: { node: edge.target.nodeId, port: edge.target.portId }
  }));

  return {
    id: draft.id,
    schemaVersion: draft.schemaVersion,
    metadata: draft.metadata,
    nodes,
    edges,
    tags: draft.tags
  };
};

export const createNodeDraftFromTemplate = (
  template: WorkflowPaletteNode,
  position: XYPosition
): WorkflowNodeDraft => {
  const nodeId = nanoid();
  const { template: manifestNode } = template;
  const schema = manifestNode.schema as WorkflowNodeSchema | undefined;
  const { parameters, results } = nodeDefaultsFromSchema(schema);

  return {
    id: nodeId,
    label: manifestNode.label,
    nodeKind: manifestNode.type,
    status: manifestNode.status,
    category: manifestNode.category,
    description: manifestNode.description,
    tags: manifestNode.tags,
    packageName: template.packageName,
    packageVersion: template.packageVersion,
    parameters,
    results,
    schema,
    ui: manifestNode.ui,
    position,
    dependencies: [],
    resources: []
  };
};

export const ensureUniqueNodeId = (existing: Record<string, WorkflowNodeDraft>, baseId?: string) => {
  if (!baseId || existing[baseId]) {
    let candidate = nanoid();
    while (existing[candidate]) {
      candidate = nanoid();
    }
    return candidate;
  }
  return baseId;
};










