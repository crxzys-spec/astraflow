import type { NodeResultDeltaEvent } from "../../client/models";

export const valuesEqual = (left: unknown, right: unknown) => {
  if (left === right) {
    return true;
  }
  if (left === undefined || right === undefined) {
    return left === right;
  }
  return JSON.stringify(left) === JSON.stringify(right);
};

type JsonContainer = Record<string, unknown> | unknown[];

type JsonPatchOp = {
  op?: string;
  path?: string;
  from?: string;
  value?: unknown;
};

const decodePointerSegment = (segment: string) => segment.replace(/~1/g, "/").replace(/~0/g, "~");

const splitJsonPointer = (pointer?: string | null): string[] | null => {
  if (!pointer || !pointer.startsWith("/")) {
    return null;
  }
  const segments = pointer
    .split("/")
    .slice(1)
    .map((part) => decodePointerSegment(part))
    .filter((part) => part.length > 0);
  return segments.length ? segments : null;
};

const applyPointerOperation = (
  target: unknown,
  segments: string[],
  op: "append" | "replace" | "remove",
  value: unknown,
): { root: unknown; changed: boolean } => {
  if (!segments.length) {
    return { root: target, changed: false };
  }
  const root: JsonContainer = Array.isArray(target)
    ? [...target]
    : target && typeof target === "object"
      ? { ...(target as Record<string, unknown>) }
      : {};
  let cursor: JsonContainer = root;
  for (let i = 0; i < segments.length - 1; i += 1) {
    const key = segments[i];
    const isIndex = /^\d+$/.test(key);
    if (Array.isArray(cursor)) {
      const index = isIndex ? Number.parseInt(key, 10) : 0;
      if (!Number.isFinite(index)) {
        return { root, changed: false };
      }
      const arr = cursor as unknown[];
      if (arr[index] == null || typeof arr[index] !== "object") {
        arr[index] = {};
      }
      cursor = arr[index] as JsonContainer;
    } else {
      const obj = cursor as Record<string, unknown>;
      if (!(key in obj) || obj[key] == null || typeof obj[key] !== "object") {
        obj[key] = {};
      }
      cursor = obj[key] as JsonContainer;
    }
  }
  const leafKey = segments[segments.length - 1];
  let changed = false;
  const isIndex = /^\d+$/.test(leafKey);
  if (op === "remove") {
    if (Array.isArray(cursor) && isIndex) {
      const arr = cursor as unknown[];
      const index = Number.parseInt(leafKey, 10);
      if (Number.isFinite(index) && index >= 0 && index < arr.length) {
        arr.splice(index, 1);
        changed = true;
      }
    } else if (!Array.isArray(cursor)) {
      const obj = cursor as Record<string, unknown>;
      if (leafKey in obj) {
        delete obj[leafKey];
        changed = true;
      }
    }
    return { root, changed };
  }

  if (op === "append") {
    const slot = (cursor as Record<string, unknown>)[leafKey];
    const arr = Array.isArray(slot) ? slot.slice() : [];
    arr.push(value);
    if (Array.isArray(cursor) && isIndex) {
      const index = Number.parseInt(leafKey, 10);
      if (Number.isFinite(index)) {
        (cursor as unknown[])[index] = arr;
        changed = true;
      }
    } else if (!Array.isArray(cursor)) {
      const obj = cursor as Record<string, unknown>;
      if (!valuesEqual(slot, arr)) {
        obj[leafKey] = arr;
        changed = true;
      }
    }
    return { root, changed };
  }

  if (op === "replace") {
    if (Array.isArray(cursor) && isIndex) {
      const index = Number.parseInt(leafKey, 10);
      if (Number.isFinite(index)) {
        const arr = cursor as unknown[];
        if (!valuesEqual(arr[index], value)) {
          arr[index] = value;
          changed = true;
        }
      }
    } else if (!Array.isArray(cursor)) {
      const obj = cursor as Record<string, unknown>;
      if (!valuesEqual(obj[leafKey], value)) {
        obj[leafKey] = value;
        changed = true;
      }
    }
  }
  return { root, changed };
};

const applyJsonPatchOperations = (
  target: unknown,
  patches: JsonPatchOp[],
): { next: unknown; changed: boolean } => {
  let current = target;
  let changed = false;
  patches.forEach((patch) => {
    const op = (patch.op || "").toLowerCase();
    const segments = splitJsonPointer(patch.path);
    if (!segments) {
      return;
    }
    if (op === "add" || op === "replace") {
      const result = applyPointerOperation(current, segments, "replace", patch.value);
      current = result.root;
      changed = changed || result.changed;
    } else if (op === "remove") {
      const result = applyPointerOperation(current, segments, "remove", undefined);
      current = result.root;
      changed = changed || result.changed;
    }
  });
  return { next: current, changed };
};

const extractDeltaValue = (payload?: Record<string, unknown> | null): unknown => {
  if (!payload || typeof payload !== "object") {
    return undefined;
  }
  if ("value" in payload) {
    return (payload as { value?: unknown }).value;
  }
  return payload;
};

export const applyResultDelta = (
  current: Record<string, unknown> | null | undefined,
  delta: Pick<NodeResultDeltaEvent, "operation" | "path" | "payload" | "patches">,
): { next: Record<string, unknown> | null; changed: boolean } => {
  const base =
    current && typeof current === "object" && !Array.isArray(current)
      ? (JSON.parse(JSON.stringify(current)) as Record<string, unknown>)
      : {};

  if (delta.operation === "patch" && Array.isArray(delta.patches)) {
    const patched = applyJsonPatchOperations(base, delta.patches as JsonPatchOp[]);
    return {
      next: (patched.next as Record<string, unknown>) ?? {},
      changed: patched.changed,
    };
  }

  const segments = splitJsonPointer(delta.path);
  if (!segments) {
    return { next: base, changed: false };
  }
  const op = (delta.operation as string | undefined) ?? "replace";
  const value = extractDeltaValue(delta.payload ?? undefined);
  const result = applyPointerOperation(
    base,
    segments,
    op === "append" ? "append" : op === "remove" ? "remove" : "replace",
    value,
  );
  return { next: result.root as Record<string, unknown>, changed: result.changed };
};

