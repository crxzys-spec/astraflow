import type { RunArtifact } from "../../api/models/runArtifact";
import type { WorkflowNodeState } from "../../api/models/workflowNodeState";

export const cloneWorkflowState = (
  state: WorkflowNodeState | null | undefined,
): WorkflowNodeState | undefined =>
  state == null ? undefined : (JSON.parse(JSON.stringify(state)) as WorkflowNodeState);

export const cloneResultRecord = (
  value: Record<string, unknown> | null | undefined,
): Record<string, unknown> | null | undefined => {
  if (value === undefined) {
    return undefined;
  }
  if (value === null) {
    return null;
  }
  return JSON.parse(JSON.stringify(value)) as Record<string, unknown>;
};

export const cloneRuntimeArtifacts = (
  artifacts: RunArtifact[] | null | undefined,
): RunArtifact[] | null | undefined => {
  if (artifacts === undefined) {
    return undefined;
  }
  if (artifacts === null) {
    return null;
  }
  return JSON.parse(JSON.stringify(artifacts)) as RunArtifact[];
};
