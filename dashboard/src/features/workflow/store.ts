﻿import { nanoid } from 'nanoid';
import { create } from 'zustand';
import { immer } from 'zustand/middleware/immer';
import type {
  WorkflowDraft,
  WorkflowEdgeDraft,
  WorkflowNodeDraft,
  WorkflowPaletteNode,
  WorkflowStore,
  WorkflowStoreState,
  WorkflowDefinition,
  XYPosition
} from './types.ts';
import {
  createNodeDraftFromTemplate,
  workflowDefinitionToDraft
} from './utils/converters.ts';

const requireWorkflow = (state: WorkflowStoreState): WorkflowDraft => {
  if (!state.workflow) {
    throw new Error('Workflow not loaded');
  }
  return state.workflow;
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

export const useWorkflowStore = create<WorkflowStore>()(
  immer((set, get) => ({
    workflow: undefined,
    selectedNodeId: undefined,

    loadWorkflow: (definition: WorkflowDefinition) => {
      set((state) => {
        state.workflow = workflowDefinitionToDraft(definition);
        state.selectedNodeId = undefined;
      });
    },

    resetWorkflow: () => {
      set((state) => {
        state.workflow = undefined;
        state.selectedNodeId = undefined;
      });
    },

    addNodeFromTemplate: (template: WorkflowPaletteNode, position: XYPosition) => {
      const nodeDraft = createNodeDraftFromTemplate(template, position);
      set((state) => {
        const workflow = requireWorkflow(state);
        // guarantee unique id
        let nodeId = nodeDraft.id;
        while (workflow.nodes[nodeId]) {
          nodeId = nanoid();
        }
        if (nodeId !== nodeDraft.id) {
          nodeDraft.id = nodeId;
        }
        workflow.nodes[nodeDraft.id] = nodeDraft;
        workflow.dirty = true;
        state.selectedNodeId = nodeDraft.id;
      });
      return get().workflow?.nodes[nodeDraft.id] ?? nodeDraft;
    },

    updateNode: (nodeId, updater) => {
      set((state) => {
        const workflow = requireWorkflow(state);
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
        const workflow = requireWorkflow(state);
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
        state.selectedNodeId = nodeId;
      });
    },

    addEdge: (edge) => {
      set((state) => {
        const workflow = requireWorkflow(state);
        const edgeId = edge.id ?? nanoid();
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
        const workflow = requireWorkflow(state);
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
        const workflow = requireWorkflow(state);
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
        const workflow = state.workflow;
        if (workflow) {
          workflow.dirty = true;
        }
      });
    }
  }))
);

export const selectWorkflow = () => useWorkflowStore.getState().workflow;

