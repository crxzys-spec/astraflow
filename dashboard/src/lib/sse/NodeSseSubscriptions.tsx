import { useEffect } from "react";
import {
  UiEventType,
  type UiEventEnvelope,
  type NodeErrorEvent,
  type NodeResultDeltaEvent,
  type NodeResultSnapshotEvent,
  type NodeStateEvent,
  type NodeStatusEvent,
} from "../../client/models";
import { useAuthStore } from "@store/authSlice";
import { useWorkflowStore } from "../../features/builder/store";
import { applyResultDelta } from "../utils/jsonDelta";
import {
  handleNodeErrorStoreUpdate,
  handleNodeResultDeltaStoreUpdate,
  handleNodeResultSnapshotStoreUpdate,
  handleNodeStateStoreUpdate,
} from "./nodeEventHandlers";
import { registerSseHandler } from "./dispatcher";

/**
 * Node-level SSE subscriptions.
 * Mirrors updates into both the runs store (for logs/detail) and the workflow store (for the canvas).
 */
export const NodeSseSubscriptions = () => {
  const canViewRuns = useAuthStore((state) =>
    state.hasRole(["admin", "run.viewer", "workflow.editor"])
  );

  useEffect(() => {
    if (!canViewRuns) {
      return;
    }

    const workflowStore = useWorkflowStore.getState();

    const getCurrentResult = (nodeId: string): Record<string, unknown> | null | undefined => {
      const workflow = workflowStore.workflow;
      if (!workflow) {
        return undefined;
      }
      const node = workflow.nodes[nodeId];
      if (node) {
        return node.results;
      }
      const host = Object.values(workflow.nodes).find((candidate) =>
        candidate.middlewares?.some((mw) => mw.id === nodeId)
      );
      const middleware = host?.middlewares?.find((mw) => mw.id === nodeId);
      return middleware?.results;
    };

    const applyResultSnapshotToWorkflow = (payload: NodeResultSnapshotEvent) => {
      workflowStore.updateNodeRuntime(payload.nodeId, {
        result: payload.content,
        artifacts: payload.artifacts ?? undefined,
        summary: payload.summary ?? undefined,
      });
    };

    const applyResultDeltaToWorkflow = (payload: NodeResultDeltaEvent) => {
      const current = getCurrentResult(payload.nodeId);
      const result = applyResultDelta(current, payload);
      if (!result.changed) {
        return;
      }
      workflowStore.updateNodeRuntime(payload.nodeId, { result: result.next ?? {} });
    };

    const applyStateToWorkflow = (nodeId: string, state: NodeStateEvent["state"]) => {
      workflowStore.updateNodeStates({ [nodeId]: state });
    };

    const handleState = (event: UiEventEnvelope) => {
      const payload = event.data as NodeStateEvent | undefined;
      if (!payload || payload.kind !== "node.state") {
        return;
      }
      handleNodeStateStoreUpdate(payload);
      applyStateToWorkflow(payload.nodeId, payload.state);
    };

    const handleStatus = (event: UiEventEnvelope) => {
      const payload = event.data as NodeStatusEvent | undefined;
      if (!payload || payload.kind !== "node.status") {
        return;
      }
      // Map status into a minimal state update so the canvas reflects progress.
      applyStateToWorkflow(payload.nodeId, { stage: payload.status } as NodeStateEvent["state"]);
    };

    const handleResultSnapshot = (event: UiEventEnvelope) => {
      const payload = event.data as NodeResultSnapshotEvent | undefined;
      if (!payload || payload.kind !== "node.result.snapshot") {
        return;
      }
      handleNodeResultSnapshotStoreUpdate(payload);
      applyResultSnapshotToWorkflow(payload);
    };

    const handleResultDelta = (event: UiEventEnvelope) => {
      const payload = event.data as NodeResultDeltaEvent | undefined;
      if (!payload || payload.kind !== "node.result.delta") {
        return;
      }
      handleNodeResultDeltaStoreUpdate(payload);
      applyResultDeltaToWorkflow(payload);
    };

    const handleError = (event: UiEventEnvelope) => {
      const payload = event.data as NodeErrorEvent | undefined;
      if (!payload || payload.kind !== "node.error") {
        return;
      }
      handleNodeErrorStoreUpdate(payload);
      applyStateToWorkflow(payload.nodeId, { stage: "failed", error: payload.error } as NodeStateEvent["state"]);
    };

    const unregisterState = registerSseHandler(UiEventType.NodeState, handleState);
    const unregisterStatus = registerSseHandler(UiEventType.NodeStatus, handleStatus);
    const unregisterSnapshot = registerSseHandler(UiEventType.NodeResultSnapshot, handleResultSnapshot);
    const unregisterDelta = registerSseHandler(UiEventType.NodeResultDelta, handleResultDelta);
    const unregisterError = registerSseHandler(UiEventType.NodeError, handleError);

    return () => {
      unregisterState();
      unregisterStatus();
      unregisterSnapshot();
      unregisterDelta();
      unregisterError();
    };
  }, [canViewRuns]);

  return null;
};
