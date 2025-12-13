import { useCallback } from "react";
import type { WorkflowDefinition, WorkflowDraft } from "../types";
import { getClientSessionId } from "../../../lib/clientSession";
import { useWorkflowStore } from "../store";
import type { RunModel, RunStartPayload, RunStatusModel } from "../../../services/runs";

export type RunMessage =
  | { type: "success"; runId?: string; text: string }
  | { type: "error"; text: string };

type UseRunActionsArgs = {
  workflow: WorkflowDraft | undefined;
  workflowKey?: string;
  canEditWorkflow: boolean;
  activeRunId?: string;
  toWorkflowDefinition: (draft: WorkflowDraft) => WorkflowDefinition;
  ensurePersistableIds: (draft: WorkflowDraft, workflowKey?: string) => WorkflowDraft;
  startRun: (payload: RunStartPayload) => Promise<RunModel>;
  cancelRun: (runId: string) => Promise<void>;
  onRunMessage: (message: RunMessage | null) => void;
  onActiveRunId: (runId?: string) => void;
  onActiveRunStatus: (status?: RunStatusModel) => void;
  getErrorMessage: (error: unknown) => string;
};

export const useRunActions = ({
  workflow,
  workflowKey,
  canEditWorkflow,
  activeRunId,
  toWorkflowDefinition,
  ensurePersistableIds,
  startRun,
  cancelRun,
  onRunMessage,
  onActiveRunId,
  onActiveRunStatus,
  getErrorMessage,
}: UseRunActionsArgs) => {
  const handleRunWorkflow = useCallback(() => {
    if (!workflow) {
      return;
    }
    if (!canEditWorkflow) {
      onRunMessage({
        type: "error",
        text: "You do not have permission to run workflows. Request workflow.editor access.",
      });
      return;
    }
    const workflowForRun = ensurePersistableIds(workflow, workflowKey);
    const definition = toWorkflowDefinition(workflowForRun);
    onRunMessage(null);

    const clientSessionId = getClientSessionId();
    startRun({ clientId: clientSessionId, workflow: definition })
      .then((run) => {
        const runId = run?.runId;
        if (runId) {
          const storeSnapshot = useWorkflowStore.getState();
          storeSnapshot.resetRunState();
          onActiveRunId(runId);
          onActiveRunStatus(run?.status ?? "queued");
        }
        onRunMessage({
          type: "success",
          runId,
          text: runId ? `Run ${runId} queued` : "Run queued successfully",
        });
      })
      .catch((error: any) => {
        const message =
          error?.response?.data?.message ?? error?.message ?? "Failed to start run";
        onRunMessage({ type: "error", text: message });
      });
  }, [
    canEditWorkflow,
    ensurePersistableIds,
    onActiveRunId,
    onActiveRunStatus,
    onRunMessage,
    startRun,
    toWorkflowDefinition,
    workflow,
    workflowKey
  ]);

  const handleCancelActiveRun = useCallback(() => {
    if (!activeRunId) {
      return;
    }
    cancelRun(activeRunId)
      .then(() => {
        onRunMessage({
          type: "success",
          runId: activeRunId,
          text: `Run ${activeRunId} cancellation requested`,
        });
        onActiveRunStatus("cancelled");
      })
      .catch((error) => {
        const message = getErrorMessage(error);
        onRunMessage({ type: "error", text: message });
      });
  }, [activeRunId, cancelRun, getErrorMessage, onActiveRunStatus, onRunMessage]);

  return { handleRunWorkflow, handleCancelActiveRun };
};
