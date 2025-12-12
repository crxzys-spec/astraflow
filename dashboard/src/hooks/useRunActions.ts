import { useCallback } from "react";
import type { QueryClient } from "@tanstack/react-query";
import type { WorkflowDefinition, WorkflowDraft } from "../features/workflow";
import { getClientSessionId } from "../lib/clientSession";
import { useWorkflowStore } from "../features/workflow";
import type { RunStatus } from "../api/models/runStatus";
import { upsertRunCaches } from "../lib/sseCache";
import type { StartRunMutationError, useStartRun, useCancelRun } from "../api/endpoints";

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
  startRun: ReturnType<typeof useStartRun>;
  cancelRun: ReturnType<typeof useCancelRun>;
  queryClient: QueryClient;
  onRunMessage: (message: RunMessage | null) => void;
  onActiveRunId: (runId?: string) => void;
  onActiveRunStatus: (status?: RunStatus) => void;
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
  queryClient,
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
    startRun.mutate(
      { data: { clientId: clientSessionId, workflow: definition } },
      {
        onSuccess: (result) => {
          const run = (result as any)?.data ?? result;
          const runId = run?.runId;
          if (runId) {
            queryClient.invalidateQueries({ queryKey: ["/api/v1/runs"] });
            upsertRunCaches(queryClient, {
              runId,
              status: run.status as RunStatus,
              definitionHash: run.definitionHash ?? "",
              clientId: run.clientId ?? "",
              startedAt: null,
              finishedAt: null
            });
            const storeSnapshot = useWorkflowStore.getState();
            storeSnapshot.resetRunState();
            onActiveRunId(runId);
            onActiveRunStatus((run?.status as RunStatus) ?? "queued");
          }
          onRunMessage({
            type: "success",
            runId,
            text: runId ? `Run ${runId} queued` : "Run queued successfully",
          });
        },
        onError: (error: StartRunMutationError) => {
          const message =
            error.response?.data?.message ?? error.message ?? "Failed to start run";
          onRunMessage({ type: "error", text: message });
        },
      }
    );
  }, [
    canEditWorkflow,
    ensurePersistableIds,
    onActiveRunId,
    onActiveRunStatus,
    onRunMessage,
    queryClient,
    startRun,
    toWorkflowDefinition,
    workflow,
    workflowKey
  ]);

  const handleCancelActiveRun = useCallback(() => {
    if (!activeRunId) {
      return;
    }
    cancelRun.mutate(
      { runId: activeRunId },
      {
        onSuccess: () => {
          onRunMessage({
            type: "success",
            runId: activeRunId,
            text: `Run ${activeRunId} cancellation requested`,
          });
          onActiveRunStatus("cancelled");
        },
        onError: (error) => {
          const message = getErrorMessage(error);
          onRunMessage({ type: "error", text: message });
        }
      }
    );
  }, [activeRunId, cancelRun, getErrorMessage, onActiveRunStatus, onRunMessage]);

  return { handleRunWorkflow, handleCancelActiveRun };
};

