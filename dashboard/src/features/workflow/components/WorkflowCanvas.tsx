import type { DragEvent, MouseEvent } from "react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import ReactFlow, { Background, useReactFlow } from "reactflow";
import type { Connection, Edge, EdgeChange, EdgeTypes, Node, NodeChange, NodeTypes } from "reactflow";
import "reactflow/dist/style.css";
import WorkflowControls from "./WorkflowControls";
import { nanoid } from "nanoid";
import { useWorkflowStore } from "../store.ts";
import { buildFlowEdges, buildFlowNodes } from "../utils/flowTransforms.ts";
import type { WorkflowEdgeDraft, XYPosition } from "../types.ts";
import { WorkflowNode } from "../nodes";
import {
  WORKFLOW_NODE_DRAG_FORMAT,
  WORKFLOW_NODE_DRAG_PACKAGE_KEY,
  WORKFLOW_NODE_DRAG_TYPE_KEY,
  WORKFLOW_NODE_DRAG_VERSION_KEY
} from "../constants.ts";

interface WorkflowCanvasProps {
  onNodeDrop?: (
    payload: { type: string; packageName?: string; packageVersion?: string },
    position: XYPosition
  ) => void;
}

const NODE_TYPES: NodeTypes = {
  workflow: WorkflowNode,
  default: WorkflowNode
};

const EDGE_TYPES: EdgeTypes = {};

const WorkflowCanvas = ({ onNodeDrop }: WorkflowCanvasProps) => {
  const workflow = useWorkflowStore((state) => {
    if (!state.workflow) {
      return undefined;
    }
    if (state.activeGraph.type === "subgraph") {
      return (
        state.subgraphDrafts.find((entry) => entry.id === state.activeGraph.subgraphId)?.definition ??
        state.workflow
      );
    }
    return state.workflow;
  });
  const activeGraph = useWorkflowStore((state) => state.activeGraph);
  const selectedNodeId = useWorkflowStore((state) => state.selectedNodeId);
  const updateNode = useWorkflowStore((state) => state.updateNode);
  const removeNode = useWorkflowStore((state) => state.removeNode);
  const setSelectedNode = useWorkflowStore((state) => state.setSelectedNode);
  const addEdge = useWorkflowStore((state) => state.addEdge);
  const removeEdge = useWorkflowStore((state) => state.removeEdge);
  const { screenToFlowPosition, getEdges } = useReactFlow();
  const [selectedEdgeId, setSelectedEdgeId] = useState<string>();

  const nodes: Node[] = useMemo(
    () => (workflow ? buildFlowNodes(workflow, selectedNodeId) : []),
    [workflow, selectedNodeId]
  );
  const edges: Edge[] = useMemo(() => (workflow ? buildFlowEdges(workflow) : []), [workflow]);

  const pendingPositionsRef = useRef<Map<string, { x: number; y: number }>>(new Map());
  const rafRef = useRef<number>();

  useEffect(
    () => () => {
      if (rafRef.current !== undefined) {
        cancelAnimationFrame(rafRef.current);
      }
    },
    []
  );

  const onNodesChange = useCallback(
    (changes: NodeChange[]) => {
      let hasPositionUpdate = false;
      changes.forEach((change) => {
        if (change.type === "position" && change.position) {
          pendingPositionsRef.current.set(change.id, {
            x: change.position.x,
            y: change.position.y
          });
          hasPositionUpdate = true;
        }
        if (change.type === "remove") {
          removeNode(change.id);
        }
      });

      if (hasPositionUpdate && rafRef.current === undefined) {
        rafRef.current = requestAnimationFrame(() => {
          pendingPositionsRef.current.forEach((position, nodeId) => {
            updateNode(nodeId, (node) => ({
              ...node,
              position
            }));
          });
          pendingPositionsRef.current.clear();
          rafRef.current = undefined;
        });
      }
    },
    [removeNode, updateNode]
  );

  const onEdgesChange = useCallback(
    (changes: EdgeChange[]) => {
      changes.forEach((change) => {
        if (change.type === "remove") {
          removeEdge(change.id);
          if (selectedEdgeId === change.id) {
            setSelectedEdgeId(undefined);
          }
        }
      });
    },
    [removeEdge, selectedEdgeId, setSelectedEdgeId]
  );

  const onConnect = useCallback(
    (connection: Connection) => {
      if (!connection.source || !connection.target || !connection.sourceHandle || !connection.targetHandle) {
        return;
      }
      const edge: WorkflowEdgeDraft = {
        id: nanoid(),
        source: { nodeId: connection.source, portId: connection.sourceHandle },
        target: { nodeId: connection.target, portId: connection.targetHandle }
      };
      addEdge(edge);
    },
    [addEdge]
  );

  const onNodeClick = useCallback(
    (_: MouseEvent, node: Node) => {
      setSelectedNode(node.id);
      setSelectedEdgeId(undefined);
    },
    [setSelectedEdgeId, setSelectedNode]
  );

  const onSelectionChange = useCallback(
    ({ nodes, edges }: { nodes: Node[]; edges: Edge[] }) => {
      if (nodes.length) {
        setSelectedNode(nodes[0].id);
        setSelectedEdgeId(undefined);
        return;
      }
      setSelectedNode(undefined);
      setSelectedEdgeId(edges.length ? edges[0].id : undefined);
    },
    [setSelectedNode, setSelectedEdgeId]
  );

  const handlePaneClick = useCallback(() => {
    setSelectedNode(undefined);
    setSelectedEdgeId(undefined);
  }, [setSelectedNode, setSelectedEdgeId]);

  const handleDragOver = useCallback((event: DragEvent<HTMLDivElement>) => {
    if (event.dataTransfer.types.includes(WORKFLOW_NODE_DRAG_FORMAT)) {
      event.preventDefault();
      event.dataTransfer.dropEffect = "copy";
    }
  }, []);

  const handleDrop = useCallback(
    (event: DragEvent<HTMLDivElement>) => {
      if (!onNodeDrop) {
        return;
      }
      const raw = event.dataTransfer.getData(WORKFLOW_NODE_DRAG_FORMAT);
      if (!raw) {
        return;
      }
      try {
        const payload = JSON.parse(raw) as Record<string, unknown>;
        const nodeType = payload[WORKFLOW_NODE_DRAG_TYPE_KEY];
        if (typeof nodeType !== "string") {
          return;
        }
        const packageNameValue = payload[WORKFLOW_NODE_DRAG_PACKAGE_KEY];
        const packageVersionValue = payload[WORKFLOW_NODE_DRAG_VERSION_KEY];
        const position = screenToFlowPosition({
          x: event.clientX,
          y: event.clientY
        });
        onNodeDrop(
          {
            type: nodeType,
            packageName: typeof packageNameValue === "string" ? packageNameValue : undefined,
            packageVersion: typeof packageVersionValue === "string" ? packageVersionValue : undefined
          },
          position
        );
      } catch (error) {
        console.error("Failed to parse dropped node payload", error);
      }
    },
    [onNodeDrop, screenToFlowPosition]
  );

  useEffect(() => {
    if (typeof window === "undefined") {
      return undefined;
    }

    const isEditableTarget = (target: EventTarget | null): boolean => {
      if (!(target instanceof HTMLElement)) {
        return false;
      }
      if (target.isContentEditable) {
        return true;
      }
      const tagName = target.tagName;
      if (tagName === "INPUT" || tagName === "TEXTAREA" || tagName === "SELECT") {
        return true;
      }
      const role = target.getAttribute("role");
      return role === "textbox" || role === "combobox";
    };

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key !== "Delete" && event.key !== "Backspace") {
        return;
      }
      const activeElement = document.activeElement;
      if (isEditableTarget(activeElement) || isEditableTarget(event.target)) {
        return;
      }
      if (selectedNodeId) {
        event.preventDefault();
        removeNode(selectedNodeId);
        return;
      }
      const selectedEdges = getEdges().filter((edge) => edge.selected);
      if (selectedEdges.length || selectedEdgeId) {
        event.preventDefault();
        const idsToRemove = selectedEdges.length ? selectedEdges.map((edge) => edge.id) : [selectedEdgeId];
        idsToRemove.forEach((edgeId) => {
          if (edgeId) {
            removeEdge(edgeId);
          }
        });
        setSelectedEdgeId(undefined);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [getEdges, removeEdge, removeNode, selectedEdgeId, selectedNodeId, setSelectedEdgeId]);

  if (!workflow) {
    return <div className="workflow-canvas__empty">Select a workflow to start.</div>;
  }

  return (
    <div className="workflow-canvas">
      <ReactFlow
        key={activeGraph.type === "subgraph" ? `subgraph-${activeGraph.subgraphId}` : "root"}
        nodes={nodes}
        edges={edges}
        nodeTypes={NODE_TYPES}
        edgeTypes={EDGE_TYPES}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onNodeClick={onNodeClick}
        onSelectionChange={onSelectionChange}
        onPaneClick={handlePaneClick}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        fitView
        className="workflow-canvas__flow"
      >
        <Background gap={16} size={1} />
        <WorkflowControls />
      </ReactFlow>
      {!nodes.length && (
        <div className="workflow-canvas__overlay">No nodes yet. Drag components from the palette.</div>
      )}
    </div>
  );
};

export default WorkflowCanvas;
