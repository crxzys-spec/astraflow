import type { DragEvent, MouseEvent } from "react";
import { useCallback, useEffect, useMemo, useRef } from "react";
import ReactFlow, { Background, Controls, useReactFlow } from "reactflow";
import type { Connection, Edge, EdgeChange, EdgeTypes, Node, NodeChange, NodeTypes } from "reactflow";
import "reactflow/dist/style.css";
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
  const workflow = useWorkflowStore((state) => state.workflow);
  const selectedNodeId = useWorkflowStore((state) => state.selectedNodeId);
  const updateNode = useWorkflowStore((state) => state.updateNode);
  const removeNode = useWorkflowStore((state) => state.removeNode);
  const setSelectedNode = useWorkflowStore((state) => state.setSelectedNode);
  const addEdge = useWorkflowStore((state) => state.addEdge);
  const removeEdge = useWorkflowStore((state) => state.removeEdge);
  const { project } = useReactFlow();

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
        }
      });
    },
    [removeEdge]
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
    },
    [setSelectedNode]
  );

  const onSelectionChange = useCallback(
    ({ nodes }: { nodes: Node[] }) => {
      if (nodes.length) {
        setSelectedNode(nodes[0].id);
      }
    },
    [setSelectedNode]
  );

  const handlePaneClick = useCallback(() => {
    setSelectedNode(undefined);
  }, [setSelectedNode]);

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
        const bounds = event.currentTarget.getBoundingClientRect();
        const position = project({
          x: event.clientX - bounds.left,
          y: event.clientY - bounds.top
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
    [onNodeDrop, project]
  );

  if (!workflow) {
    return <div className="workflow-canvas__empty">Select a workflow to start.</div>;
  }

  return (
    <div className="workflow-canvas">
      <ReactFlow
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
        <Controls position="top-right" />
      </ReactFlow>
      {!nodes.length && (
        <div className="workflow-canvas__overlay">No nodes yet. Drag components from the palette.</div>
      )}
    </div>
  );
};

export default WorkflowCanvas;
