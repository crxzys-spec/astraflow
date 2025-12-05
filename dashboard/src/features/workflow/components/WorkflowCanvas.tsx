import type { DragEvent, MouseEvent } from "react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import ReactFlow, { Background, applyNodeChanges, useReactFlow } from "reactflow";
import type { Connection, Edge, EdgeChange, EdgeTypes, Node, NodeChange, NodeTypes } from "reactflow";
import "reactflow/dist/style.css";
import WorkflowControls from "./WorkflowControls";
import { useWorkflowStore } from "../store.ts";
import { buildFlowEdges, buildFlowNodes } from "../utils/flowTransforms.ts";
import type { WorkflowEdgeDraft, XYPosition, WorkflowPaletteNode } from "../types.ts";
import { WorkflowNode } from "../nodes";
import { generateId } from "../utils/id.ts";
import {
  WORKFLOW_NODE_DRAG_FORMAT,
  WORKFLOW_NODE_DRAG_PACKAGE_KEY,
  WORKFLOW_NODE_DRAG_TYPE_KEY,
  WORKFLOW_NODE_DRAG_VERSION_KEY
} from "../constants.ts";
import { getGetPackageQueryOptions } from "../../../api/endpoints";

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

type WorkflowNodeData = {
  nodeId: string;
  label?: string;
  status?: string;
  stage?: string;
  role?: string;
  progress?: number;
  message?: string;
  lastUpdatedAt?: string;
  packageName?: string;
  packageVersion?: string;
  adapter?: string;
  handler?: string;
  widgets?: unknown[];
  fallbackInputPorts?: string[];
  fallbackOutputPorts?: string[];
  middlewares?: unknown[];
  attachedMiddlewares?: { id: string; label: string; node: unknown; index: number }[];
};

const arraysShallowEqual = <T,>(
  left?: T[] | null,
  right?: T[] | null,
  comparator: (a: T, b: T) => boolean = (a, b) => a === b
): boolean => {
  if (left === right) {
    return true;
  }
  const a = left ?? [];
  const b = right ?? [];
  if (a.length !== b.length) {
    return false;
  }
  for (let index = 0; index < a.length; index += 1) {
    if (!comparator(a[index], b[index])) {
      return false;
    }
  }
  return true;
};

const attachedMiddlewaresEqual = (
  left?: WorkflowNodeData["attachedMiddlewares"],
  right?: WorkflowNodeData["attachedMiddlewares"]
): boolean =>
  arraysShallowEqual(left, right, (a, b) => a.id === b.id && a.label === b.label && a.node === b.node && a.index === b.index);

const nodeDataEqual = (left?: Node["data"], right?: Node["data"]): boolean => {
  if (left === right) {
    return true;
  }
  const a = left as WorkflowNodeData | undefined;
  const b = right as WorkflowNodeData | undefined;
  if (!a || !b) {
    return false;
  }
  const comparableKeys: (keyof WorkflowNodeData)[] = [
    "nodeId",
    "label",
    "status",
    "stage",
    "role",
    "progress",
    "message",
    "lastUpdatedAt",
    "packageName",
    "packageVersion",
    "adapter",
    "handler"
  ];
  if (comparableKeys.some((key) => a[key] !== b[key])) {
    return false;
  }
  return (
    arraysShallowEqual(a.widgets, b.widgets) &&
    arraysShallowEqual(a.fallbackInputPorts, b.fallbackInputPorts) &&
    arraysShallowEqual(a.fallbackOutputPorts, b.fallbackOutputPorts) &&
    arraysShallowEqual(a.middlewares, b.middlewares) &&
    attachedMiddlewaresEqual(a.attachedMiddlewares, b.attachedMiddlewares)
  );
};

const WorkflowCanvas = ({ onNodeDrop }: WorkflowCanvasProps) => {
  const queryClient = useQueryClient();
  const workflow = useWorkflowStore((state) => {
    if (!state.workflow) {
      return undefined;
    }
    if (state.activeGraph.type === "subgraph") {
      const subgraph = state.subgraphDrafts.find((entry) => entry.id === state.activeGraph.subgraphId)?.definition;
      return subgraph ?? state.workflow;
    }
    return state.workflow;
  });
  const activeGraph = useWorkflowStore((state) => state.activeGraph);
  const subgraphDrafts = useWorkflowStore((state) => state.subgraphDrafts);
  const selectedNodeIds = useWorkflowStore((state) => state.selectedNodeIds);
  const removeNode = useWorkflowStore((state) => state.removeNode);
  const setNodePositions = useWorkflowStore((state) => state.setNodePositions);
  const captureHistory = useWorkflowStore((state) => state.captureHistory);
  const setActiveGraph = useWorkflowStore((state) => state.setActiveGraph);
  const setSelectedNodes = useWorkflowStore((state) => state.setSelectedNodes);
  const addEdge = useWorkflowStore((state) => state.addEdge);
  const removeEdge = useWorkflowStore((state) => state.removeEdge);
  const convertSelectionToSubgraph = useWorkflowStore((state) => state.convertSelectionToSubgraph);
  const { screenToFlowPosition, getEdges } = useReactFlow();
  const [selectedEdgeId, setSelectedEdgeId] = useState<string>();
  const [contextMenu, setContextMenu] = useState<
    | { type: "node"; id: string; position: { x: number; y: number } }
    | { type: "edge"; id: string; position: { x: number; y: number } }
    | { type: "selection"; position: { x: number; y: number } }
    | undefined
  >(undefined);
  const isMac = useMemo(() => typeof navigator !== "undefined" && /mac/i.test(navigator.platform), []);
  const multiSelectionKeyCode = useMemo(() => (isMac ? "Meta" : "Control"), [isMac]);
  const graphKey = useMemo(
    () =>
      workflow
        ? activeGraph.type === "subgraph"
          ? `subgraph:${activeGraph.subgraphId ?? "unknown"}:${workflow.id}`
          : `root:${workflow.id}`
        : "none",
    [activeGraph, workflow]
  );
  const lastGraphKeyRef = useRef<string | null>(null);

  const baseNodes: Node[] = useMemo(
    () => (workflow ? buildFlowNodes(workflow, selectedNodeIds) : []),
    [workflow, selectedNodeIds]
  );
  const [nodes, setNodes] = useState<Node[]>(baseNodes);
  const edges: Edge[] = useMemo(() => (workflow ? buildFlowEdges(workflow) : []), [workflow]);
  const pendingPositionsRef = useRef<Map<string, { x: number; y: number }>>(new Map());
  const dragHistoryRecordedRef = useRef<boolean>(false);

  useEffect(() => {
    // Incremental workflow updates can arrive frequently; merge them to avoid remounting every node.
    setNodes((current) => {
      if (lastGraphKeyRef.current !== graphKey) {
        lastGraphKeyRef.current = graphKey;
        pendingPositionsRef.current.clear();
        dragHistoryRecordedRef.current = false;
        return baseNodes;
      }

      const pendingPositions = pendingPositionsRef.current;
      const currentMap = new Map(current.map((node) => [node.id, node]));
      let changed = current.length !== baseNodes.length;

      const merged = baseNodes.map((node) => {
        const existing = currentMap.get(node.id);
        const pendingPosition = pendingPositions.get(node.id);
        const targetPosition = pendingPosition ?? existing?.position ?? node.position;
        if (!existing) {
          changed = true;
          return { ...node, position: targetPosition };
        }
        const samePosition =
          existing.position?.x === targetPosition?.x && existing.position?.y === targetPosition?.y;
        const sameSelection = existing.selected === node.selected;
        const sameMeta = existing.type === node.type && existing.draggable === node.draggable;
        const sameData = nodeDataEqual(existing.data, node.data);
        if (samePosition && sameSelection && sameMeta && sameData) {
          return existing;
        }
        changed = true;
        const nextPosition = pendingPosition && existing.position ? existing.position : targetPosition;
        return { ...existing, ...node, data: node.data, position: nextPosition, selected: node.selected };
      });

      if (changed) {
        return merged;
      }
      return current;
    });
    // Keep dragging nodes' positions so incremental updates do not override them.
    if (pendingPositionsRef.current.size) {
      const aliveIds = new Set(baseNodes.map((node) => node.id));
      pendingPositionsRef.current.forEach((_, nodeId) => {
        if (!aliveIds.has(nodeId)) {
          pendingPositionsRef.current.delete(nodeId);
        }
      });
    } else if (lastGraphKeyRef.current === graphKey) {
      dragHistoryRecordedRef.current = false;
    }
  }, [baseNodes, graphKey]);

  useEffect(() => {
    if (activeGraph.type === "subgraph") {
      const exists = subgraphDrafts.some((entry) => entry.id === activeGraph.subgraphId);
      if (!exists) {
        setActiveGraph({ type: "root" }, { recordHistory: false });
      }
    }
  }, [activeGraph, setActiveGraph, subgraphDrafts]);
  useEffect(() => {
    const handlePointerUp = () => {
      if (pendingPositionsRef.current.size) {
        const positions: Record<string, XYPosition> = {};
        pendingPositionsRef.current.forEach((position, nodeId) => {
          positions[nodeId] = position;
        });
        pendingPositionsRef.current.clear();
        setNodePositions(positions, { record: false });
      }
      dragHistoryRecordedRef.current = false;
    };
    window.addEventListener("pointerup", handlePointerUp);
    return () => window.removeEventListener("pointerup", handlePointerUp);
  }, [setNodePositions]);

  const onNodesChange = useCallback(
    (changes: NodeChange[]) => {
      let selectionChanged = false;
      let nextSelectedNodeIds: string[] | null = null;

      setNodes((current) => {
        const next = applyNodeChanges(changes, current);
        if (changes.some((change) => change.type === "select")) {
          selectionChanged = true;
          nextSelectedNodeIds = next.filter((node) => node.selected).map((node) => node.id);
        }
        return next;
      });

      let hasPositionUpdate = false;
      let draggingEnded = false;
      changes.forEach((change) => {
        if (change.type === "position" && change.position) {
          pendingPositionsRef.current.set(change.id, {
            x: change.position.x,
            y: change.position.y,
          });
          hasPositionUpdate = true;
          if (change.dragging === false) {
            draggingEnded = true;
          }
        }
        if (change.type === "remove") {
          pendingPositionsRef.current.delete(change.id);
          removeNode(change.id);
        }
      });

      if (hasPositionUpdate && !dragHistoryRecordedRef.current) {
        captureHistory();
        dragHistoryRecordedRef.current = true;
      }

      if (draggingEnded) {
        if (pendingPositionsRef.current.size) {
          const positions: Record<string, XYPosition> = {};
          pendingPositionsRef.current.forEach((position, nodeId) => {
            positions[nodeId] = position;
          });
          pendingPositionsRef.current.clear();
          setNodePositions(positions, { record: false });
        }
        dragHistoryRecordedRef.current = false;
      }

      if (selectionChanged && nextSelectedNodeIds) {
        setSelectedNodes(nextSelectedNodeIds);
        setSelectedEdgeId(undefined);
      }
    },
    [captureHistory, removeNode, setNodePositions, setSelectedEdgeId, setSelectedNodes]
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
        id: generateId(),
        source: { nodeId: connection.source, portId: connection.sourceHandle },
        target: { nodeId: connection.target, portId: connection.targetHandle }
      };
      addEdge(edge);
    },
    [addEdge]
  );

  const onSelectionChange = useCallback(
    ({ nodes, edges }: { nodes: Node[]; edges: Edge[] }) => {
      if (nodes.length) {
        setSelectedNodes(nodes.map((node) => node.id));
        setSelectedEdgeId(undefined);
        return;
      }
      setSelectedNodes([]);
      setSelectedEdgeId(edges.length ? edges[0].id : undefined);
    },
    [setSelectedEdgeId, setSelectedNodes]
  );

  const handlePaneClick = useCallback(() => {
    setSelectedNodes([]);
    setSelectedEdgeId(undefined);
    setContextMenu(undefined);
  }, [setSelectedEdgeId, setSelectedNodes]);

  const handleDragOver = useCallback((event: DragEvent<HTMLDivElement>) => {
    // Always allow drop so Chrome/Edge can populate the payload on drop.
    event.preventDefault();
    event.dataTransfer.dropEffect = "copy";
  }, []);

  const handleDrop = useCallback(
    (event: DragEvent<HTMLDivElement>) => {
      event.preventDefault();
      event.stopPropagation();
      if (!onNodeDrop) {
        return;
      }
      const tryProcessPayload = (raw: string | null | undefined) => {
        if (!raw) {
          return false;
        }
        try {
          const payload = JSON.parse(raw) as Record<string, unknown>;
          const nodeType = payload[WORKFLOW_NODE_DRAG_TYPE_KEY];
          if (typeof nodeType !== "string") {
            return false;
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
          return true;
        } catch (error) {
          console.error("Failed to parse dropped node payload", error);
          return false;
        }
      };

      const raw =
        event.dataTransfer.getData(WORKFLOW_NODE_DRAG_FORMAT) ||
        event.dataTransfer.getData("application/reactflow") ||
        event.dataTransfer.getData("text/plain");

      if (tryProcessPayload(raw)) {
        return;
      }

      const items = Array.from(event.dataTransfer.items || []);
      const candidate = items.find((item) =>
        [WORKFLOW_NODE_DRAG_FORMAT, "application/reactflow", "text/plain"].includes(item.type)
      );
      if (candidate && typeof candidate.getAsString === "function") {
        candidate.getAsString((text) => {
          tryProcessPayload(text);
        });
      }
    },
    [onNodeDrop, screenToFlowPosition]
  );

  const closeContextMenu = useCallback(() => setContextMenu(undefined), []);

  useEffect(() => {
    const handler = () => setContextMenu(undefined);
    window.addEventListener("click", handler);
    return () => window.removeEventListener("click", handler);
  }, []);

  const handleNodeContextMenu = useCallback(
    (event: MouseEvent, node: Node) => {
      event.preventDefault();
      event.stopPropagation();
      const isSelected = selectedNodeIds.includes(node.id);
      setContextMenu({
        type: isSelected ? "selection" : "node",
        id: node.id,
        position: { x: event.clientX, y: event.clientY }
      });
    },
    [selectedNodeIds]
  );

  const handleEdgeContextMenu = useCallback((event: MouseEvent, edge: Edge) => {
    event.preventDefault();
    event.stopPropagation();
    setContextMenu({ type: "edge", id: edge.id, position: { x: event.clientX, y: event.clientY } });
  }, []);

  const handlePaneContextMenu = useCallback((event: MouseEvent) => {
    event.preventDefault();
    setContextMenu(undefined);
  }, []);

  const deleteSelectedNodes = useCallback(() => {
    if (!selectedNodeIds.length) {
      return;
    }
    selectedNodeIds.forEach((id) => removeNode(id));
    closeContextMenu();
  }, [closeContextMenu, removeNode, selectedNodeIds]);

  const deleteSingleNode = useCallback(
    (nodeId: string) => {
      removeNode(nodeId);
      closeContextMenu();
    },
    [closeContextMenu, removeNode]
  );

  const deleteEdgeById = useCallback(
    (edgeId: string) => {
      removeEdge(edgeId);
      closeContextMenu();
    },
    [closeContextMenu, removeEdge]
  );

  const convertSelection = useCallback(async () => {
    let template: WorkflowPaletteNode | undefined;
    try {
      const response = await queryClient.ensureQueryData(
        getGetPackageQueryOptions("system", undefined, { query: { staleTime: 5 * 60 * 1000 } })
      );
      const definition = response?.data;
      const containerManifest = definition?.manifest?.nodes?.find(
        (node: { type?: string }) => node.type === "workflow.container"
      );
      if (containerManifest) {
        template = {
          template: containerManifest,
          packageName: definition?.name,
          packageVersion: definition?.version
        };
      }
    } catch (error) {
      console.error("Failed to load system container definition", error);
    }
    const result = convertSelectionToSubgraph(template);
    if (!result.ok) {
      console.error(result.error ?? "Failed to convert selection to subgraph.");
    }
    closeContextMenu();
  }, [closeContextMenu, convertSelectionToSubgraph, queryClient]);

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
      if (selectedNodeIds.length) {
        event.preventDefault();
        selectedNodeIds.forEach((id) => removeNode(id));
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
  }, [getEdges, removeEdge, removeNode, selectedEdgeId, selectedNodeIds, setSelectedEdgeId]);

  if (!workflow) {
    return <div className="workflow-canvas__empty">Select a workflow to start.</div>;
  }

  return (
    <div className="workflow-canvas" onDrop={handleDrop} onDragOver={handleDragOver}>
      <ReactFlow
        key={activeGraph.type === "subgraph" ? `subgraph-${activeGraph.subgraphId}` : "root"}
        nodes={nodes}
        edges={edges}
        nodeTypes={NODE_TYPES}
        edgeTypes={EDGE_TYPES}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onSelectionChange={onSelectionChange}
        onPaneClick={handlePaneClick}
        onPaneContextMenu={handlePaneContextMenu}
        onNodeContextMenu={handleNodeContextMenu}
        onEdgeContextMenu={handleEdgeContextMenu}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        selectNodesOnDrag={false}
        selectionKeyCode="Shift"
        multiSelectionKeyCode={multiSelectionKeyCode}
        selectionOnDrag
        fitView
        className="workflow-canvas__flow"
      >
        <Background gap={16} size={1} />
        <WorkflowControls />
      </ReactFlow>
      {contextMenu && (
        <div
          className="workflow-contextmenu"
          style={{ top: contextMenu.position.y, left: contextMenu.position.x }}
          onClick={(event) => event.stopPropagation()}
        >
          {contextMenu.type === "node" && (
            <>
              <button type="button" onClick={() => deleteSingleNode(contextMenu.id)}>
                删除节点
              </button>
            </>
          )}
          {contextMenu.type === "edge" && (
            <>
              <button type="button" onClick={() => deleteEdgeById(contextMenu.id)}>
                删除线条
              </button>
            </>
          )}
          {contextMenu.type === "selection" && (
            <>
              <button type="button" onClick={convertSelection}>
                选中转为子图
              </button>
              <button type="button" onClick={deleteSelectedNodes}>
                删除所选
              </button>
            </>
          )}
        </div>
      )}
      {!nodes.length && (
        <div className="workflow-canvas__overlay" style={{ pointerEvents: "none" }}>
          No nodes yet. Drag components from the palette.
        </div>
      )}
    </div>
  );
};

export default WorkflowCanvas;
