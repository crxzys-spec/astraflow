import type { WorkflowNodeDraft, NodeWidgetDefinition } from "../types";
import type { UIBindingMode } from "../../../api/models/uIBindingMode";

type BindingRoot = "parameters" | "results";

export interface BindingResolution {
  root: BindingRoot;
  path: string[];
}

const decodePointerSegment = (segment: string) => segment.replace(/~1/g, "/").replace(/~0/g, "~");

export const resolveBindingPath = (path: string): BindingResolution | undefined => {
  if (!path) {
    return undefined;
  }
  let segments: string[];
  if (path.startsWith("/")) {
    segments = path
      .split("/")
      .filter(Boolean)
      .map((part) => decodePointerSegment(part));
  } else {
    segments = path.split(".").map((part) => part.replace(/\[|\]/g, "")).filter(Boolean);
  }
  if (!segments.length) {
    return undefined;
  }
  const [root, ...rest] = segments as [BindingRoot, ...string[]];
  if (root !== "parameters" && root !== "results") {
    return undefined;
  }
  return { root, path: rest };
};

export const getBindingValue = (node: WorkflowNodeDraft, resolution: BindingResolution): unknown => {
  const source = resolution.root === "parameters" ? node.parameters : node.results;
  return resolution.path.reduce<unknown>((accumulator, key) => {
    if (accumulator && typeof accumulator === "object") {
      return (accumulator as Record<string, unknown>)[key];
    }
    return undefined;
  }, source);
};

const cloneContainer = (value: unknown): Record<string, unknown> | unknown[] => {
  if (Array.isArray(value)) {
    return [...value];
  }
  if (value && typeof value === "object") {
    return { ...(value as Record<string, unknown>) };
  }
  return {};
};

const applyValue = (target: unknown, path: string[], value: unknown): unknown => {
  if (!path.length) {
    return value;
  }
  const [head, ...rest] = path;
  const container = cloneContainer(target);
  const currentChild = (container as Record<string, unknown>)[head];
  (container as Record<string, unknown>)[head] = rest.length ? applyValue(currentChild, rest, value) : value;
  return container;
};

export const setBindingValue = (
  node: WorkflowNodeDraft,
  resolution: BindingResolution,
  value: unknown
): WorkflowNodeDraft => {
  if (resolution.root === "parameters") {
    const nextParameters = applyValue(node.parameters, resolution.path, value);
    return {
      ...node,
      parameters: nextParameters as Record<string, unknown>
    };
  }
  const nextResults = applyValue(node.results, resolution.path, value);
  return {
    ...node,
    results: nextResults as Record<string, unknown>
  };
};

export const resolveWidgetBinding = (widget: NodeWidgetDefinition): BindingResolution | undefined =>
  resolveBindingPath(widget.binding?.path ?? "");

const editableModes: UIBindingMode[] = ["write", "two_way"];

export const isBindingEditable = (mode?: UIBindingMode): boolean => !!mode && editableModes.includes(mode);

