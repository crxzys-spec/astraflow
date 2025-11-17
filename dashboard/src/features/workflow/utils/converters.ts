import { nanoid } from "nanoid";
import type { EdgeEndpoint } from "../../../api/models/edgeEndpoint";
import type { Workflow as WorkflowDefinition } from "../../../api/models/workflow";
import type { WorkflowEdge } from "../../../api/models/workflowEdge";
import type { WorkflowNode } from "../../../api/models/workflowNode";
import { WorkflowNodeStatus } from "../../../api/models/workflowNodeStatus";
import type { WorkflowMetadata } from "../../../api/models/workflowMetadata";
import type { WorkflowNodeSchema } from "../../../api/models/workflowNodeSchema";
import type { WorkflowNodeState } from "../../../api/models/workflowNodeState";
import type { NodeUI } from "../../../api/models/nodeUI";
import type { UIBinding } from "../../../api/models/uIBinding";
import { UIBindingMode } from "../../../api/models/uIBindingMode";
import type { UIPort } from "../../../api/models/uIPort";
import type { UIWidget } from "../../../api/models/uIWidget";
import type { ManifestBinding } from "../../../api/models/manifestBinding";
import type { ManifestNodeUI } from "../../../api/models/manifestNodeUI";
import type { ManifestPort } from "../../../api/models/manifestPort";
import type { ManifestWidget } from "../../../api/models/manifestWidget";
import type {
  WorkflowDraft,
  WorkflowEdgeDraft,
  WorkflowEdgeEndpointDraft,
  WorkflowNodeDraft,
  WorkflowPaletteNode,
  XYPosition,
} from "../types.ts";
import { buildDefaultsFromSchema } from "./schemaDefaults.ts";
import type { JsonSchema } from "./schemaDefaults.ts";

const clone = <T>(value: T): T =>
  value === undefined ? value : (JSON.parse(JSON.stringify(value)) as T);

const coerceOptional = <T>(value: T | null | undefined): T | undefined =>
  value === null || value === undefined ? undefined : value;

const sanitizeTags = (
  tags?: (string | null | undefined)[],
): string[] | undefined => {
  if (!tags) {
    return undefined;
  }
  const filtered = tags.filter(
    (tag): tag is string => typeof tag === "string" && tag.length > 0,
  );
  return filtered.length ? filtered : undefined;
};

const normalizeBinding = (binding?: UIBinding): UIBinding => {
  if (!binding) {
    return { path: "", mode: UIBindingMode.write };
  }
  const normalisedMode =
    binding.mode === UIBindingMode.read ||
    binding.mode === UIBindingMode.two_way
      ? binding.mode
      : UIBindingMode.write;
  return {
    path: binding.path ?? "",
    mode: normalisedMode,
  };
};

const mapPorts = (ports?: UIPort[] | null): UIPort[] | undefined => {
  if (!ports) {
    return undefined;
  }
  return ports.map((port) => ({
    key: port.key,
    label: port.label,
    binding: normalizeBinding(port.binding),
  }));
};

const mapWidgets = (widgets?: UIWidget[] | null): UIWidget[] | undefined => {
  if (!widgets) {
    return undefined;
  }
  return widgets.map((widget) => {
    const serialized: UIWidget = {
      key: widget.key,
      label: widget.label,
      component: widget.component,
      binding: normalizeBinding(widget.binding),
    };
    const options = coerceOptional(widget.options);
    if (options !== undefined) {
      serialized.options = options;
    }
    return serialized;
  });
};

const sanitizeNodeUi = (ui?: NodeUI | null): NodeUI | undefined => {
  if (!ui) {
    return undefined;
  }
  const sanitized: NodeUI = {};
  const inputs = mapPorts(ui.inputPorts);
  if (inputs !== undefined) {
    sanitized.inputPorts = inputs;
  }
  const outputs = mapPorts(ui.outputPorts);
  if (outputs !== undefined) {
    sanitized.outputPorts = outputs;
  }
  const widgets = mapWidgets(ui.widgets);
  if (widgets !== undefined) {
    sanitized.widgets = widgets;
  }
  return sanitized;
};

const sanitizeMetadata = (
  metadata: WorkflowMetadata | undefined,
  fallbackName: string,
): WorkflowMetadata => {
  const safeName = metadata?.name ?? fallbackName;
  const sanitized: WorkflowMetadata = {
    name: safeName,
  };
  if (metadata?.description !== undefined && metadata.description !== null) {
    sanitized.description = metadata.description;
  }
  const tags = sanitizeTags(metadata?.tags);
  if (tags !== undefined) {
    sanitized.tags = tags;
  }
  if (metadata?.environment !== undefined && metadata.environment !== null) {
    sanitized.environment = metadata.environment;
  }
  const namespaceValue =
    metadata?.namespace && metadata.namespace.trim().length > 0
      ? metadata.namespace.trim()
      : "default";
  sanitized.namespace = namespaceValue;
  const originValue =
    metadata?.originId && metadata.originId.trim().length > 0
      ? metadata.originId.trim()
      : fallbackName;
  sanitized.originId = originValue;
  return sanitized;
};

const coerceBinding = (binding?: ManifestBinding): UIBinding => {
  const rawMode = binding?.mode;
  const safeMode =
    rawMode === UIBindingMode.read || rawMode === UIBindingMode.two_way
      ? rawMode
      : UIBindingMode.write;

  return {
    path: binding?.path ?? "",
    mode: safeMode,
  };
};

const coercePorts = (ports?: ManifestPort[]): UIPort[] | undefined =>
  ports?.map((port) => ({
    key: port.key,
    label: port.label,
    binding: coerceBinding(port.binding),
  }));

const coerceWidgets = (widgets?: ManifestWidget[]): UIWidget[] | undefined =>
  widgets?.map((widget) => {
    const coerced: UIWidget = {
      key: widget.key,
      label: widget.label,
      component: widget.component,
      binding: coerceBinding(widget.binding),
    };
    const options = coerceOptional(widget.options);
    if (options !== undefined) {
      coerced.options = options as UIWidget["options"];
    }
    return coerced;
  });

const coerceManifestUi = (ui?: ManifestNodeUI | null): NodeUI | undefined => {
  if (!ui) {
    return undefined;
  }
  const manifestWithOutputs = ui as ManifestNodeUI & {
    outputPorts?: ManifestPort[];
  };
  const coerced: NodeUI = {
    inputPorts: coercePorts(ui.inputPorts),
    outputPorts: coercePorts(manifestWithOutputs.outputPorts),
    widgets: coerceWidgets(ui.widgets),
  };
  return sanitizeNodeUi(coerced);
};

export const nodeDefaultsFromSchema = (
  schema?: WorkflowNodeSchema | Record<string, unknown> | null,
) => {
  const container = (schema ?? {}) as {
    parameters?: JsonSchema;
    results?: JsonSchema;
  };
  const parametersSchema = container.parameters as JsonSchema | undefined;
  const resultsSchema = container.results as JsonSchema | undefined;
  return {
    parameters: parametersSchema
      ? buildDefaultsFromSchema(parametersSchema)
      : {},
    results: resultsSchema ? buildDefaultsFromSchema(resultsSchema) : {},
  };
};

const mapEndpoint = (endpoint: EdgeEndpoint): WorkflowEdgeEndpointDraft => ({
  nodeId: endpoint.node,
  portId: endpoint.port,
});

const mapEdgeToDraft = (edge: WorkflowEdge): WorkflowEdgeDraft => ({
  id: edge.id ?? nanoid(),
  source: mapEndpoint(edge.source),
  target: mapEndpoint(edge.target),
});

export const workflowDefinitionToDraft = (
  definition: WorkflowDefinition,
): WorkflowDraft => {
  const nodes: Record<string, WorkflowNodeDraft> = {};

  definition.nodes.forEach((node: WorkflowNode) => {
    const { parameters: defaultParams, results: defaultResults } =
      nodeDefaultsFromSchema(node.schema);
    const draft: WorkflowNodeDraft = {
      id: node.id,
      label: node.label,
      nodeKind: node.type,
      status: node.status ?? WorkflowNodeStatus.draft,
      category: node.category ?? "uncategorised",
      description: coerceOptional(node.description),
      tags: sanitizeTags(node.tags),
      packageName: node.package?.name,
      packageVersion: node.package?.version,
      parameters: clone(node.parameters ?? defaultParams),
      results: clone(node.results ?? defaultResults),
      schema: node.schema ?? undefined,
      ui: sanitizeNodeUi(node.ui),
      position: {
        x: node.position?.x ?? 0,
        y: node.position?.y ?? 0,
      },
      dependencies: [],
      resources: [],
    state: node.state ? (clone(node.state) as WorkflowNodeState) : undefined,
  };
  nodes[draft.id] = draft;
});

  const edges: WorkflowEdgeDraft[] = (definition.edges ?? []).map(
    mapEdgeToDraft,
  );

  edges.forEach((edge) => {
    const target = nodes[edge.target.nodeId];
    if (target && !target.dependencies.includes(edge.source.nodeId)) {
      target.dependencies.push(edge.source.nodeId);
    }
  });

  return {
    id: definition.id,
    schemaVersion: definition.schemaVersion,
    metadata: sanitizeMetadata(definition.metadata, definition.id),
    tags: sanitizeTags(definition.tags),
    nodes,
    edges,
    dirty: false,
  };
};

export const workflowDraftToDefinition = (
  draft: WorkflowDraft,
): WorkflowDefinition => {
  const nodes: WorkflowNode[] = Object.values(draft.nodes).map((node) => {
    const workflowNode: WorkflowNode = {
      id: node.id,
      type: node.nodeKind,
      package: {
        name: node.packageName ?? "",
        version: node.packageVersion ?? "",
      },
      status: (node.status ?? WorkflowNodeStatus.draft) as WorkflowNodeStatus,
      category: node.category ?? "uncategorised",
      label: node.label,
      position: { x: node.position.x, y: node.position.y },
      parameters: clone(node.parameters),
      results: clone(node.results),
      ui: sanitizeNodeUi(node.ui),
    };
    const description = coerceOptional(node.description);
    if (description !== undefined) {
      workflowNode.description = description;
    }
    const tags = sanitizeTags(node.tags);
    if (tags !== undefined) {
      workflowNode.tags = tags;
    }
    const schema = coerceOptional(node.schema);
    if (schema !== undefined) {
      workflowNode.schema = schema;
    }
    return workflowNode;
  });

  const edges: WorkflowEdge[] = draft.edges.map((edge) => ({
    id: edge.id,
    source: { node: edge.source.nodeId, port: edge.source.portId },
    target: { node: edge.target.nodeId, port: edge.target.portId },
  }));

  const metadata: WorkflowMetadata = sanitizeMetadata(draft.metadata, draft.id);

  return {
    id: draft.id,
    schemaVersion: draft.schemaVersion,
    metadata,
    nodes,
    edges,
    tags: sanitizeTags(draft.tags),
  };
};

export const createNodeDraftFromTemplate = (
  template: WorkflowPaletteNode,
  position: XYPosition,
): WorkflowNodeDraft => {
  const nodeId = nanoid();
  const { template: manifestNode } = template;
  const schema = manifestNode.schema as WorkflowNodeSchema | undefined;
  const { parameters, results } = nodeDefaultsFromSchema(schema);

  return {
    id: nodeId,
    label: manifestNode.label,
    nodeKind: manifestNode.type,
    status: manifestNode.status ?? WorkflowNodeStatus.draft,
    category: manifestNode.category,
    description: coerceOptional(manifestNode.description),
    tags: sanitizeTags(manifestNode.tags),
    packageName: template.packageName,
    packageVersion: template.packageVersion,
    parameters,
    results,
    schema,
    ui: coerceManifestUi(manifestNode.ui),
    position,
    dependencies: [],
    resources: [],
    state: undefined,
  };
};

export const ensureUniqueNodeId = (
  existing: Record<string, WorkflowNodeDraft>,
  baseId?: string,
) => {
  if (!baseId || existing[baseId]) {
    let candidate = nanoid();
    while (existing[candidate]) {
      candidate = nanoid();
    }
    return candidate;
  }
  return baseId;
};
