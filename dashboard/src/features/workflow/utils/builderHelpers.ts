import { generateId, isValidUuid } from "./id";
import type { WorkflowDefinition, WorkflowDraft } from "../types";

export const slugifyValue = (value: string): string =>
  value
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 80);

export const normalizeVisibility = (value?: string | null): "private" | "public" | "internal" => {
  if (value === "public" || value === "internal") {
    return value;
  }
  return "private";
};

export const createEmptyWorkflow = (id: string, name: string): WorkflowDefinition => ({
  id,
  schemaVersion: "2025-10",
  metadata: {
    name,
    namespace: "default",
    originId: id,
  },
  nodes: [],
  edges: [],
});

export const ensurePersistableIds = (draft: WorkflowDraft, workflowKey?: string): WorkflowDraft => {
  const needsNewId = !workflowKey || workflowKey === "new" || !isValidUuid(draft.id);
  const id = needsNewId ? generateId() : draft.id;
  const originId = isValidUuid(draft.metadata?.originId) ? draft.metadata?.originId : id;

  return {
    ...draft,
    id,
    metadata: {
      ...(draft.metadata ?? {}),
      originId,
    },
  };
};

