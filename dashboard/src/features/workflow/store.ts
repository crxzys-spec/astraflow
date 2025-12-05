import { create } from 'zustand';
import { immer } from 'zustand/middleware/immer';
import type { WorkflowNodeState } from '../../api/models/workflowNodeState';
import type {
  InlineSubgraphResult,
  WorkflowDraft,
  WorkflowEdgeDraft,
  WorkflowMiddlewareDraft,
  WorkflowNodeDraft,
  WorkflowNodeStateUpdateMap,
  WorkflowPaletteNode,
  WorkflowStore,
  WorkflowStoreState,
  WorkflowDefinition,
  WorkflowSubgraphDraftEntry,
  WorkflowGraphScope,
  XYPosition,
  ConvertSelectionResult,
  NodePortDefinition,
  WorkflowPaletteNode
} from './types.ts';
import {
  createNodeDraftFromTemplate,
  nodeDefaultsFromSchema,
  workflowDefinitionToDraft
} from './utils/converters.ts';
import { generateId } from './utils/id.ts';
import { CONTAINER_PARAM_KEY } from './constants.ts';

const HISTORY_LIMIT = 100;

type HistoryEntry = {
  workflow?: WorkflowDraft;
  subgraphDrafts: WorkflowSubgraphDraftEntry[];
  selectedNodeId?: string;
  selectedNodeIds: string[];
  activeGraph: WorkflowGraphScope;
};

const cloneDraft = <T>(value: T): T =>
  value === undefined ? value : (JSON.parse(JSON.stringify(value)) as T);

const captureHistoryEntry = (state: WorkflowStoreState): HistoryEntry => ({
  workflow: cloneDraft(state.workflow),
  subgraphDrafts: cloneDraft(state.subgraphDrafts),
  selectedNodeId: state.selectedNodeId,
  selectedNodeIds: [...state.selectedNodeIds],
  activeGraph: state.activeGraph,
});

const applyHistoryEntry = (state: WorkflowStoreState, entry: HistoryEntry) => {
  state.workflow = cloneDraft(entry.workflow);
  state.subgraphDrafts = cloneDraft(entry.subgraphDrafts);
  state.selectedNodeId = entry.selectedNodeId;
  state.selectedNodeIds = [...entry.selectedNodeIds];
  state.activeGraph = entry.activeGraph;
};

const recordHistory = (state: WorkflowStoreState) => {
  // Only record when a workflow is loaded; runtime overlays should not be captured.
  if (!state.workflow) {
    return;
  }
  const snapshot = captureHistoryEntry(state);
  state.history.past.push(snapshot);
  if (state.history.past.length > HISTORY_LIMIT) {
    state.history.past.shift();
  }
  state.history.future = [];
};

const requireWorkflow = (state: WorkflowStoreState): WorkflowDraft => {
  if (!state.workflow) {
    throw new Error('Workflow not loaded');
  }
  return state.workflow;
};

const defaultGraphScope: WorkflowGraphScope = { type: 'root' };

const requireActiveGraph = (state: WorkflowStoreState): WorkflowDraft => {
  if (state.activeGraph.type === 'subgraph') {
    const entry = state.subgraphDrafts.find((item) => item.id === state.activeGraph.subgraphId);
    if (!entry) {
      throw new Error(`Subgraph ${state.activeGraph.subgraphId} not loaded`);
    }
    return entry.definition;
  }
  return requireWorkflow(state);
};

const forEachDraft = (
  state: WorkflowStoreState,
  iterator: (draft: WorkflowDraft) => void,
) => {
  if (state.workflow) {
    iterator(state.workflow);
  }
  state.subgraphDrafts.forEach((entry) => iterator(entry.definition));
};

const ensureDependency = (node: WorkflowNodeDraft, dependencyId: string) => {
  if (!node.dependencies.includes(dependencyId)) {
    node.dependencies.push(dependencyId);
  }
};

const removeDependency = (node: WorkflowNodeDraft | undefined, dependencyId: string) => {
  if (!node) return;
  node.dependencies = node.dependencies.filter((id) => id !== dependencyId);
};

const cloneState = (value: WorkflowNodeState | null | undefined): WorkflowNodeState | undefined => {
  if (value == null) {
    return undefined;
  }
  return JSON.parse(JSON.stringify(value)) as WorkflowNodeState;
};

const statesEqual = (left: WorkflowNodeState | undefined, right: WorkflowNodeState | undefined): boolean =>
  JSON.stringify(left ?? null) === JSON.stringify(right ?? null);

const getContainerConfig = (
  node: WorkflowNodeDraft | undefined
): { subgraphId?: string } | undefined => {
  if (!node?.parameters) {
    return undefined;
  }
  const config = node.parameters[CONTAINER_PARAM_KEY];
  if (!config || typeof config !== "object") {
    return undefined;
  }
  return config as { subgraphId?: string };
};

const computeNodeClusterCenter = (nodes: WorkflowNodeDraft[], fallback: XYPosition): XYPosition => {
  if (!nodes.length) {
    return fallback;
  }
  let minX = Number.POSITIVE_INFINITY;
  let maxX = Number.NEGATIVE_INFINITY;
  let minY = Number.POSITIVE_INFINITY;
  let maxY = Number.NEGATIVE_INFINITY;
  nodes.forEach((node) => {
    const position = node.position ?? fallback;
    minX = Math.min(minX, position.x);
    maxX = Math.max(maxX, position.x);
    minY = Math.min(minY, position.y);
    maxY = Math.max(maxY, position.y);
  });
  if (!Number.isFinite(minX) || !Number.isFinite(maxX) || !Number.isFinite(minY) || !Number.isFinite(maxY)) {
    return fallback;
  }
  return {
    x: (minX + maxX) / 2,
    y: (minY + maxY) / 2,
  };
};

const rewriteBindingPrefixValue = (
  prefix: string | undefined,
  targetSubgraphId: string,
  nodeIdMap: Map<string, string>
): string | undefined => {
  if (!prefix || !prefix.startsWith("@")) {
    return prefix;
  }
  const body = prefix.slice(1);
  if (!body.length) {
    return prefix;
  }
  const segments = body.split(".");
  if (!segments.length) {
    return prefix;
  }
  if (segments[0] !== targetSubgraphId) {
    return prefix;
  }
  const nodeTokenIndex = segments.findIndex((segment) => segment.startsWith("#"));
  const aliasSegments = nodeTokenIndex === -1 ? segments : segments.slice(0, nodeTokenIndex);
  const remainingAliases = aliasSegments.slice(1);
  const tailSegments = nodeTokenIndex === -1 ? [] : segments.slice(nodeTokenIndex);
  if (tailSegments.length && tailSegments[0].startsWith("#")) {
    const currentNodeId = tailSegments[0].slice(1);
    const mappedId = nodeIdMap.get(currentNodeId) ?? currentNodeId;
    tailSegments[0] = `#${mappedId}`;
  }
  if (remainingAliases.length) {
    const aliasPrefix = `@${remainingAliases.join(".")}`;
    if (!tailSegments.length) {
      return aliasPrefix;
    }
    return `${aliasPrefix}.${tailSegments.join(".")}`;
  }
  if (!tailSegments.length) {
    return undefined;
  }
  return tailSegments.join(".");
};

const rewriteBindingsInNode = (
  node: WorkflowNodeDraft | WorkflowMiddlewareDraft | undefined,
  targetSubgraphId: string,
  nodeIdMap: Map<string, string>
) => {
  if (!node?.ui) {
    return;
  }
  const applyBindingRewrite = (binding?: { prefix?: string }) => {
    if (!binding) {
      return;
    }
    const nextPrefix = rewriteBindingPrefixValue(binding.prefix, targetSubgraphId, nodeIdMap);
    if (nextPrefix !== binding.prefix) {
      binding.prefix = nextPrefix;
    }
  };
  const rewritePorts = (ports?: NodePortDefinition[]) => {
    ports?.forEach((port) => {
      applyBindingRewrite(port.binding);
    });
  };
  rewritePorts(node.ui.inputPorts);
  rewritePorts(node.ui.outputPorts);
  node.ui.widgets?.forEach((widget) => {
    applyBindingRewrite(widget.binding);
  });
};

const rewriteBindingsInWorkflow = (
  draft: WorkflowDraft | undefined,
  targetSubgraphId: string,
  nodeIdMap: Map<string, string>
) => {
  if (!draft) {
    return;
  }
  Object.values(draft.nodes).forEach((node) => {
    rewriteBindingsInNode(node, targetSubgraphId, nodeIdMap);
    node.middlewares?.forEach((middleware) => {
      rewriteBindingsInNode(middleware, targetSubgraphId, nodeIdMap);
    });
  });
};

const rewriteBindingsAcrossStore = (
  state: WorkflowStoreState,
  targetSubgraphId: string,
  nodeIdMap: Map<string, string>
) => {
  rewriteBindingsInWorkflow(state.workflow, targetSubgraphId, nodeIdMap);
  state.subgraphDrafts.forEach((entry) => {
    rewriteBindingsInWorkflow(entry.definition, targetSubgraphId, nodeIdMap);
  });
};

export const useWorkflowStore = create<WorkflowStore>()(
  immer((set, get) => ({
    workflow: undefined,
    selectedNodeId: undefined,
    selectedNodeIds: [],
    subgraphDrafts: [],
    activeGraph: defaultGraphScope,
    history: {
      past: [],
      future: [],
    },

    loadWorkflow: (definition: WorkflowDefinition) => {
      set((state) => {
        state.workflow = workflowDefinitionToDraft(definition);
        const subgraphDrafts: WorkflowSubgraphDraftEntry[] =
          definition.subgraphs?.map((subgraph) => ({
            id: subgraph.id,
            metadata: subgraph.metadata,
            definition: workflowDefinitionToDraft(subgraph.definition),
          })) ?? [];
        state.subgraphDrafts = subgraphDrafts;
        state.selectedNodeId = undefined;
        state.selectedNodeIds = [];
        state.activeGraph = defaultGraphScope;
        state.history = { past: [], future: [] };
      });
    },

    resetWorkflow: () => {
      set((state) => {
        state.workflow = undefined;
        state.selectedNodeId = undefined;
        state.selectedNodeIds = [];
        state.subgraphDrafts = [];
        state.activeGraph = defaultGraphScope;
        state.history = { past: [], future: [] };
      });
    },
    setPreviewImage: (preview) => {
      set((state) => {
        recordHistory(state);
        if (state.workflow) {
          state.workflow.previewImage = preview ?? undefined;
        }
      });
    },

    addNodeFromTemplate: (template: WorkflowPaletteNode, position: XYPosition) => {
      const nodeDraft = createNodeDraftFromTemplate(template, position);
      let addedNode: WorkflowNodeDraft | undefined;
      set((state) => {
        recordHistory(state);
        const workflow = requireActiveGraph(state);
        // guarantee unique id
        let nodeId = nodeDraft.id;
        while (workflow.nodes[nodeId]) {
          nodeId = generateId();
        }
        if (nodeId !== nodeDraft.id) {
          nodeDraft.id = nodeId;
        }
        workflow.nodes[nodeDraft.id] = nodeDraft;
        workflow.dirty = true;
        state.selectedNodeId = nodeDraft.id;
        state.selectedNodeIds = [nodeDraft.id];
        addedNode = workflow.nodes[nodeDraft.id];
      });
      return addedNode ?? nodeDraft;
    },

    updateNode: (nodeId, updater) => {
      set((state) => {
        recordHistory(state);
        const workflow = requireActiveGraph(state);
        const node = workflow.nodes[nodeId];
        if (!node) {
          return;
        }
        workflow.nodes[nodeId] = updater(node);
        workflow.dirty = true;
      });
    },

    removeNode: (nodeId) => {
      set((state) => {
        recordHistory(state);
        const workflow = requireActiveGraph(state);
        if (!workflow.nodes[nodeId]) {
          return;
        }
        delete workflow.nodes[nodeId];
        workflow.edges = workflow.edges.filter((edge) => edge.source.nodeId !== nodeId && edge.target.nodeId !== nodeId);
        Object.values(workflow.nodes).forEach((node) => {
          node.dependencies = node.dependencies.filter((dep) => dep !== nodeId);
        });
        if (state.selectedNodeId === nodeId) {
          state.selectedNodeId = undefined;
        }
        if (state.selectedNodeIds.length) {
          state.selectedNodeIds = state.selectedNodeIds.filter((id) => id !== nodeId);
        }
        workflow.dirty = true;
      });
    },

    setSelectedNode: (nodeId) => {
      set((state) => {
        state.selectedNodeId = nodeId;
        state.selectedNodeIds = nodeId ? [nodeId] : [];
      });
    },

    setSelectedNodes: (nodeIds) => {
      set((state) => {
        const uniqueIds = Array.from(new Set(nodeIds));
        state.selectedNodeIds = uniqueIds;
        state.selectedNodeId = uniqueIds[0];
      });
    },

    toggleSelectedNode: (nodeId) => {
      set((state) => {
        const exists = state.selectedNodeIds.includes(nodeId);
        if (exists) {
          state.selectedNodeIds = state.selectedNodeIds.filter((id) => id !== nodeId);
          if (state.selectedNodeId === nodeId) {
            state.selectedNodeId = state.selectedNodeIds[0];
          }
          return;
        }
        state.selectedNodeIds = [...state.selectedNodeIds, nodeId];
        state.selectedNodeId = nodeId;
      });
    },
    setNodePosition: (nodeId, position, options) => {
      set((state) => {
        const workflow = requireActiveGraph(state);
        const node = workflow.nodes[nodeId];
        if (!node) {
          return;
        }
        const prev = node.position;
        if (prev && prev.x === position.x && prev.y === position.y) {
          return;
        }
        if (options?.record !== false) {
          recordHistory(state);
        }
        node.position = { ...position };
        workflow.dirty = true;
      });
    },
    setNodePositions: (positions, options) => {
      set((state) => {
        const workflow = requireActiveGraph(state);
        const entries = Object.entries(positions);
        const updates: [string, XYPosition][] = entries
          .map(([nodeId, position]) => {
            const node = workflow.nodes[nodeId];
            if (!node) {
              return undefined;
            }
            const prev = node.position;
            if (prev && prev.x === position.x && prev.y === position.y) {
              return undefined;
            }
            return [nodeId, position] as [string, XYPosition];
          })
          .filter((item): item is [string, XYPosition] => Boolean(item));
        if (!updates.length) {
          return;
        }
        if (options?.record !== false) {
          recordHistory(state);
        }
        updates.forEach(([nodeId, position]) => {
          const node = workflow.nodes[nodeId];
          if (node) {
            node.position = { ...position };
          }
        });
        workflow.dirty = true;
      });
    },
    captureHistory: () => {
      set((state) => {
        recordHistory(state);
      });
    },

    addEdge: (edge) => {
      set((state) => {
        recordHistory(state);
        const workflow = requireActiveGraph(state);
        const edgeId = edge.id ?? generateId();
        const existingIndex = workflow.edges.findIndex((e) => e.id === edgeId);
        const nextEdge: WorkflowEdgeDraft = existingIndex >= 0 ? { ...workflow.edges[existingIndex], ...edge, id: edgeId } : { ...edge, id: edgeId };
        if (existingIndex >= 0) {
          workflow.edges[existingIndex] = nextEdge;
        } else {
          workflow.edges.push(nextEdge);
        }
        const targetNode = workflow.nodes[nextEdge.target.nodeId];
        if (targetNode) {
          ensureDependency(targetNode, nextEdge.source.nodeId);
        }
        workflow.dirty = true;
      });
    },

    updateEdge: (edgeId, updater) => {
      set((state) => {
        recordHistory(state);
        const workflow = requireActiveGraph(state);
        const index = workflow.edges.findIndex((edge) => edge.id === edgeId);
        if (index === -1) {
          return;
        }
        const updated = updater(workflow.edges[index]);
        workflow.edges[index] = updated;
        const targetNode = workflow.nodes[updated.target.nodeId];
        if (targetNode) {
          ensureDependency(targetNode, updated.source.nodeId);
        }
        workflow.dirty = true;
      });
    },

    removeEdge: (edgeId) => {
      set((state) => {
        recordHistory(state);
        const workflow = requireActiveGraph(state);
        const edge = workflow.edges.find((item) => item.id === edgeId);
        workflow.edges = workflow.edges.filter((item) => item.id !== edgeId);
        if (edge) {
          const targetNode = workflow.nodes[edge.target.nodeId];
          removeDependency(targetNode, edge.source.nodeId);
        }
        workflow.dirty = true;
      });
    },

    markDirty: () => {
      set((state) => {
        recordHistory(state);
        const workflow = requireActiveGraph(state);
        workflow.dirty = true;
      });
    },

    updateNodeStates: (updates: WorkflowNodeStateUpdateMap) => {
      set((state) => {
        forEachDraft(state, (workflow) => {
          Object.entries(updates).forEach(([nodeId, nextState]) => {
            const node = workflow.nodes[nodeId];
            const normalized = cloneState(nextState);
            if (node) {
              if (!statesEqual(node.state, normalized)) {
                node.state = normalized;
              }
              return;
            }
            // middleware updates: find the host that owns this middleware id
            const host = Object.values(workflow.nodes).find((candidate) =>
              candidate.middlewares?.some((mw) => mw.id === nodeId)
            );
            if (host?.middlewares) {
              host.middlewares = host.middlewares.map((mw) =>
                mw.id === nodeId ? { ...mw, state: normalized } : mw
              );
            }
          });
        });
      });
    },

    updateNodeRuntime: (nodeId, payload) => {
      set((state) => {
        forEachDraft(state, (workflow) => {
          const node = workflow.nodes[nodeId];
          const applyRuntime = (target: any) => {
            if (payload.result !== undefined) {
              target.results =
                payload.result === null
                  ? {}
                  : (JSON.parse(JSON.stringify(payload.result)) as Record<string, unknown>);
            }
            if (payload.artifacts !== undefined) {
              target.runtimeArtifacts = payload.artifacts
                ? JSON.parse(JSON.stringify(payload.artifacts))
                : null;
            }
            if (payload.summary !== undefined) {
              target.runtimeSummary = payload.summary ?? null;
            }
          };
          if (node) {
            applyRuntime(node);
            return;
          }
          const host = Object.values(workflow.nodes).find((candidate) =>
            candidate.middlewares?.some((mw) => mw.id === nodeId)
          );
          if (host?.middlewares) {
            host.middlewares = host.middlewares.map((mw) => {
              if (mw.id === nodeId) {
                const copy = { ...mw };
                applyRuntime(copy);
                return copy;
              }
              return mw;
            });
          }
        });
      });
    },

    resetRunState: () => {
      set((state) => {
        forEachDraft(state, (workflow) => {
          Object.values(workflow.nodes).forEach((node) => {
            node.state = undefined;
            node.runtimeArtifacts = null;
            node.runtimeSummary = null;
            const defaults = nodeDefaultsFromSchema(node.schema);
            node.results = JSON.parse(JSON.stringify(defaults.results ?? {}));
          });
        });
      });
    },

    setActiveGraph: (scope, options) => {
      set((state) => {
        const shouldRecord = options?.recordHistory ?? true;
        if (shouldRecord) {
          recordHistory(state);
        }
        if (scope.type === 'subgraph') {
          const exists = state.subgraphDrafts.some((entry) => entry.id === scope.subgraphId);
          state.activeGraph = exists ? scope : defaultGraphScope;
        } else {
          state.activeGraph = scope;
        }
        state.selectedNodeId = undefined;
        state.selectedNodeIds = [];
      });
    },
    undo: () => {
      set((state) => {
        const previous = state.history.past.pop();
        if (!previous) {
          return;
        }
        const currentSnapshot = captureHistoryEntry(state);
        state.history.future.push(currentSnapshot);
        applyHistoryEntry(state, previous);
      });
    },
    redo: () => {
      set((state) => {
        const next = state.history.future.pop();
        if (!next) {
          return;
        }
        const currentSnapshot = captureHistoryEntry(state);
        state.history.past.push(currentSnapshot);
        applyHistoryEntry(state, next);
      });
    },
    canUndo: () => {
      const { past } = get().history;
      return past.length > 0;
    },
    canRedo: () => {
      const { future } = get().history;
      return future.length > 0;
    },
    inlineSubgraphIntoActiveGraph: (containerNodeId, subgraphIdOverride) => {
      const outcome: InlineSubgraphResult = { ok: false };
      set((state) => {
        let rootWorkflow: WorkflowDraft;
        try {
          rootWorkflow = requireWorkflow(state);
        } catch (error) {
          outcome.error = error instanceof Error ? error.message : 'Workflow not loaded';
          return;
        }
        // default to current graph when a concrete container is provided (so subgraph edits work),
        // otherwise operate on the root workflow when resolving by subgraph id.
        const targetWorkflow =
          containerNodeId && state.activeGraph.type === 'subgraph'
            ? requireActiveGraph(state)
            : rootWorkflow;
        let targetContainerId = containerNodeId;
        if (!targetContainerId && subgraphIdOverride && state.workflow) {
          const matchingContainers = Object.values(rootWorkflow.nodes).filter(
            (node) =>
              node.nodeKind === 'workflow.container' &&
              getContainerConfig(node)?.subgraphId === subgraphIdOverride
          );
          if (matchingContainers.length === 1) {
            targetContainerId = matchingContainers[0].id;
          } else if (matchingContainers.length === 0) {
            outcome.error = 'No container references this subgraph in the current workflow.';
            return;
          } else {
            outcome.error = 'Multiple containers reference this subgraph; select one in the canvas and try again.';
            return;
          }
        }
        const containerNode =
          targetContainerId
            ? targetWorkflow.nodes[targetContainerId] ?? rootWorkflow.nodes[targetContainerId]
            : undefined;
        if (!containerNode) {
          outcome.error = 'Select a container node or provide a valid reference.';
          return;
        }
        if (containerNode.nodeKind !== 'workflow.container') {
          outcome.error = 'Only container nodes support subgraph inlining.';
          return;
        }
        const containerConfig = getContainerConfig(containerNode);
        const subgraphId = subgraphIdOverride ?? containerConfig?.subgraphId;
        if (!subgraphId) {
          outcome.error = 'Container is missing a subgraph reference.';
          return;
        }
        const subgraphEntry = state.subgraphDrafts.find((entry) => entry.id === subgraphId);
        if (!subgraphEntry) {
          outcome.error = 'Referenced subgraph is not loaded.';
          return;
        }
        recordHistory(state);
        const subgraphClone = cloneDraft(subgraphEntry.definition);
        const sourceNodes = Object.values(subgraphClone.nodes ?? {});
        const nodeIdMap = new Map<string, string>();
        const reservedIds = new Set(Object.keys(targetWorkflow.nodes));
        sourceNodes.forEach((node) => {
          let nextId = node.id;
          while (reservedIds.has(nextId)) {
            nextId = generateId();
          }
          nodeIdMap.set(node.id, nextId);
          reservedIds.add(nextId);
        });
        let serialized = JSON.stringify(subgraphClone);
        nodeIdMap.forEach((nextId, originalId) => {
          if (nextId !== originalId) {
            serialized = serialized.split(originalId).join(nextId);
          }
        });
        const normalizedSubgraph = JSON.parse(serialized) as WorkflowDraft;
        const nodesToInsert = Object.values(normalizedSubgraph.nodes ?? {});
        const anchorPosition = containerNode.position ?? { x: 0, y: 0 };
        const clusterCenter = computeNodeClusterCenter(nodesToInsert, anchorPosition);
        const insertedNodeIds: string[] = [];
        nodesToInsert.forEach((node) => {
          const position = node.position ?? anchorPosition;
          node.position = {
            x: position.x - clusterCenter.x + anchorPosition.x,
            y: position.y - clusterCenter.y + anchorPosition.y,
          };
          node.dependencies = node.dependencies.filter((id) => id !== containerNodeId);
          targetWorkflow.nodes[node.id] = node;
          insertedNodeIds.push(node.id);
        });
        const additionalEdges: WorkflowEdgeDraft[] = (normalizedSubgraph.edges ?? []).map((edge) => ({
          id: generateId(),
          source: { ...edge.source },
          target: { ...edge.target },
        }));
        targetWorkflow.edges = targetWorkflow.edges.filter(
          (edge) => edge.source.nodeId !== containerNodeId && edge.target.nodeId !== containerNodeId
        );
        targetWorkflow.edges.push(...additionalEdges);
        additionalEdges.forEach((edge) => {
          const targetNode = targetWorkflow.nodes[edge.target.nodeId];
          if (targetNode) {
            ensureDependency(targetNode, edge.source.nodeId);
          }
        });
        Object.values(targetWorkflow.nodes).forEach((node) => {
          node.dependencies = node.dependencies.filter((dep) => dep !== containerNodeId);
        });
        delete targetWorkflow.nodes[containerNodeId];
        targetWorkflow.dirty = true;
        rootWorkflow.dirty = true;
        rewriteBindingsAcrossStore(state, subgraphId, nodeIdMap);
        // remove subgraph entry after dissolving
        state.subgraphDrafts = state.subgraphDrafts.filter((entry) => entry.id !== subgraphId);
        if (state.workflow?.subgraphs) {
          state.workflow.subgraphs = state.workflow.subgraphs.filter((entry) => entry.id !== subgraphId);
        }
        if (state.activeGraph.type === 'subgraph' && state.activeGraph.subgraphId === subgraphId) {
          state.activeGraph = defaultGraphScope;
        }
        if (insertedNodeIds.length) {
          state.selectedNodeId = insertedNodeIds[0];
          state.selectedNodeIds = insertedNodeIds;
        } else {
          state.selectedNodeId = undefined;
          state.selectedNodeIds = [];
        }
        outcome.ok = true;
      });
      return outcome;
    },
    convertSelectionToSubgraph: (containerTemplate?: WorkflowPaletteNode) => {
      const outcome: ConvertSelectionResult = { ok: false };
      set((state) => {
        const selection = state.selectedNodeIds;
        if (!selection.length) {
          outcome.error = 'Select at least one node to convert.';
          return;
        }
        let targetWorkflow: WorkflowDraft;
        try {
          targetWorkflow = requireActiveGraph(state);
        } catch (error) {
          outcome.error = error instanceof Error ? error.message : 'Workflow not loaded';
          return;
        }
        const selectionSet = new Set(selection);
        const selectedNodes = selection
          .map((id) => targetWorkflow.nodes[id])
          .filter((node): node is WorkflowNodeDraft => Boolean(node));
        if (!selectedNodes.length) {
          outcome.error = 'Selected nodes are missing from the current graph.';
          return;
        }
        recordHistory(state);
        const subgraphId = generateId();
        const subgraphDefinitionId = subgraphId;
        const subgraphMetadata = { name: `Subgraph ${subgraphId.slice(0, 6)}` };
        const internalEdges = targetWorkflow.edges.filter(
          (edge) => selectionSet.has(edge.source.nodeId) && selectionSet.has(edge.target.nodeId)
        );
        const incomingEdges = targetWorkflow.edges.filter(
          (edge) => !selectionSet.has(edge.source.nodeId) && selectionSet.has(edge.target.nodeId)
        );
        const outgoingEdges = targetWorkflow.edges.filter(
          (edge) => selectionSet.has(edge.source.nodeId) && !selectionSet.has(edge.target.nodeId)
        );
        const subgraphDraft: WorkflowDraft = {
          id: subgraphDefinitionId,
          schemaVersion: targetWorkflow.schemaVersion ?? '1.0.0',
          metadata: subgraphMetadata,
          nodes: selectedNodes.reduce<Record<string, WorkflowNodeDraft>>((acc, node) => {
            acc[node.id] = cloneDraft(node);
            return acc;
          }, {}),
          edges: internalEdges.map((edge) => cloneDraft(edge)),
          subgraphs: [],
          dirty: false,
        };
        state.subgraphDrafts.push({
          id: subgraphId,
          definition: subgraphDraft,
          metadata: subgraphMetadata,
        });
        if (state.workflow) {
          if (!state.workflow.subgraphs) {
            state.workflow.subgraphs = [];
          }
          const existingIndex = state.workflow.subgraphs.findIndex((entry) => entry.id === subgraphId);
          const subgraphEntry = {
            id: subgraphId,
            metadata: subgraphMetadata,
            definition: subgraphDraft,
          };
          if (existingIndex >= 0) {
            state.workflow.subgraphs[existingIndex] = subgraphEntry;
          } else {
            state.workflow.subgraphs.push(subgraphEntry);
          }
        }

        // remove selected nodes and related edges
        targetWorkflow.edges = targetWorkflow.edges.filter(
          (edge) => !selectionSet.has(edge.source.nodeId) && !selectionSet.has(edge.target.nodeId)
        );
        Object.values(targetWorkflow.nodes).forEach((node) => {
          node.dependencies = node.dependencies.filter((dep) => !selectionSet.has(dep));
        });
        selection.forEach((id) => {
          delete targetWorkflow.nodes[id];
        });

        const anchor = computeNodeClusterCenter(selectedNodes, { x: 0, y: 0 });
        const containerId = generateId();
        const baseContainer: WorkflowNodeDraft | undefined = containerTemplate
          ? createNodeDraftFromTemplate(containerTemplate, anchor)
          : undefined;
        const inputPorts: NodePortDefinition[] = baseContainer?.ui?.inputPorts
          ? baseContainer.ui.inputPorts.map((port) => ({ ...port }))
          : [];
        const outputPorts: NodePortDefinition[] = baseContainer?.ui?.outputPorts
          ? baseContainer.ui.outputPorts.map((port) => ({ ...port }))
          : [];
        const containerDependencies = new Set<string>();
        const inputPortKeyMap = new Map<string, string>();
        const outputPortKeyMap = new Map<string, string>();
        const reservePortKey = (base: string, existing: NodePortDefinition[]) => {
          let key = base;
          let counter = 1;
          const keys = new Set(existing.map((port) => port.key));
          while (keys.has(key)) {
            key = `${base}-${counter}`;
            counter += 1;
          }
          return key;
        };

        incomingEdges.forEach((edge) => {
          const targetPortKey = edge.target.portId || edge.target.nodeId;
          if (!inputPortKeyMap.has(targetPortKey)) {
            const portKey = reservePortKey(`in-${targetPortKey}`, inputPorts);
            inputPortKeyMap.set(targetPortKey, portKey);
            inputPorts.push({
              key: portKey,
              label: portKey,
              binding: { path: '', mode: 'write' },
            });
          }
          const mappedPort = inputPortKeyMap.get(targetPortKey) as string;
          const newEdge: WorkflowEdgeDraft = {
            id: generateId(),
            source: { ...edge.source },
            target: { nodeId: containerId, portId: mappedPort },
          };
          targetWorkflow.edges.push(newEdge);
          containerDependencies.add(edge.source.nodeId);
        });

        outgoingEdges.forEach((edge) => {
          const sourcePortKey = edge.source.portId || edge.source.nodeId;
          if (!outputPortKeyMap.has(sourcePortKey)) {
            const portKey = reservePortKey(`out-${sourcePortKey}`, outputPorts);
            outputPortKeyMap.set(sourcePortKey, portKey);
            outputPorts.push({
              key: portKey,
              label: portKey,
              binding: { path: '/results/', mode: 'read' },
            });
          }
          const mappedPort = outputPortKeyMap.get(sourcePortKey) as string;
          const newEdge: WorkflowEdgeDraft = {
            id: generateId(),
            source: { nodeId: containerId, portId: mappedPort },
            target: { ...edge.target },
          };
          targetWorkflow.edges.push(newEdge);
          const targetNode = targetWorkflow.nodes[edge.target.nodeId];
          if (targetNode) {
            ensureDependency(targetNode, containerId);
          }
        });

        const containerNode: WorkflowNodeDraft = {
          id: containerId,
          label: subgraphMetadata.name ?? containerId,
          role: baseContainer?.role ?? 'container',
          nodeKind: baseContainer?.nodeKind ?? 'workflow.container',
          status: baseContainer?.status ?? 'draft',
          category: baseContainer?.category ?? 'container',
          description: baseContainer?.description,
          tags: baseContainer?.tags,
          packageName: baseContainer?.packageName,
          packageVersion: baseContainer?.packageVersion,
          adapter: baseContainer?.adapter,
          handler: baseContainer?.handler,
          parameters: (() => {
            const baseParams = baseContainer?.parameters ? cloneDraft(baseContainer.parameters) : {};
            return {
              ...baseParams,
              [CONTAINER_PARAM_KEY]: {
                ...(baseParams?.[CONTAINER_PARAM_KEY] as Record<string, unknown> | undefined),
                subgraphId: subgraphDefinitionId,
              },
            };
          })(),
          results: baseContainer?.results ? cloneDraft(baseContainer.results) : {},
          schema: baseContainer?.schema,
          ui: {
            inputPorts,
            outputPorts,
            widgets: baseContainer?.ui?.widgets ? [...baseContainer.ui.widgets] : [],
          },
          position: anchor,
          dependencies: Array.from(new Set([...(baseContainer?.dependencies ?? []), ...containerDependencies])),
          middlewares: baseContainer?.middlewares ? cloneDraft(baseContainer.middlewares) : [],
          resources: [],
          affinity: baseContainer?.affinity,
          concurrencyKey: baseContainer?.concurrencyKey,
          metadata: baseContainer?.metadata,
          state: undefined,
          runtimeArtifacts: undefined,
          runtimeSummary: undefined,
        };
        targetWorkflow.nodes[containerId] = containerNode;
        targetWorkflow.dirty = true;
        if (state.workflow) {
          state.workflow.dirty = true;
        }
        state.selectedNodeId = containerId;
        state.selectedNodeIds = [containerId];
        outcome.ok = true;
        outcome.subgraphId = subgraphId;
        outcome.containerId = containerId;
      });
      return outcome;
    },
  }))
);

export const selectWorkflow = () => useWorkflowStore.getState().workflow;
