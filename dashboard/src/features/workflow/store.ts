import { create } from 'zustand';
import { immer } from 'zustand/middleware/immer';
import type { WorkflowNodeState } from '../../api/models/workflowNodeState';
import type {
  WorkflowDraft,
  WorkflowEdgeDraft,
  WorkflowNodeDraft,
  WorkflowNodeStateUpdateMap,
  WorkflowPaletteNode,
  WorkflowStore,
  WorkflowStoreState,
  WorkflowDefinition,
  WorkflowSubgraphDraftEntry,
  WorkflowGraphScope,
  XYPosition
} from './types.ts';
import {
  createNodeDraftFromTemplate,
  nodeDefaultsFromSchema,
  workflowDefinitionToDraft
} from './utils/converters.ts';
import { generateId } from './utils/id.ts';

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

export const useWorkflowStore = create<WorkflowStore>()(
  immer((set, get) => ({
    workflow: undefined,
    selectedNodeId: undefined,
    subgraphDrafts: [],
    activeGraph: defaultGraphScope,

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
        state.activeGraph = defaultGraphScope;
      });
    },

    resetWorkflow: () => {
      set((state) => {
        state.workflow = undefined;
        state.selectedNodeId = undefined;
        state.subgraphDrafts = [];
        state.activeGraph = defaultGraphScope;
      });
    },
    setPreviewImage: (preview) => {
      set((state) => {
        if (state.workflow) {
          state.workflow.previewImage = preview ?? undefined;
        }
      });
    },

    addNodeFromTemplate: (template: WorkflowPaletteNode, position: XYPosition) => {
      const nodeDraft = createNodeDraftFromTemplate(template, position);
      let addedNode: WorkflowNodeDraft | undefined;
      set((state) => {
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
        addedNode = workflow.nodes[nodeDraft.id];
      });
      return addedNode ?? nodeDraft;
    },

    updateNode: (nodeId, updater) => {
      set((state) => {
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
        workflow.dirty = true;
      });
    },

    setSelectedNode: (nodeId) => {
      set((state) => {
        if (state.selectedNodeId === nodeId) {
          return;
        }
        state.selectedNodeId = nodeId;
      });
    },

    addEdge: (edge) => {
      set((state) => {
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

    setActiveGraph: (scope) => {
      set((state) => {
        if (scope.type === 'subgraph') {
          const exists = state.subgraphDrafts.some((entry) => entry.id === scope.subgraphId);
          state.activeGraph = exists ? scope : defaultGraphScope;
        } else {
          state.activeGraph = scope;
        }
        state.selectedNodeId = undefined;
      });
    },
  }))
);

export const selectWorkflow = () => useWorkflowStore.getState().workflow;

