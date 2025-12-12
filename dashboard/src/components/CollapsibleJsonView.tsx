import type { ReactElement } from "react";

export type JsonPrimitive = string | number | boolean | null;

export type JsonValue =
  | JsonPrimitive
  | JsonValue[]
  | {
      [key: string]: JsonValue;
    };

const isRecord = (value: JsonValue): value is Record<string, JsonValue> =>
  typeof value === "object" && value !== null && !Array.isArray(value);

export const normalizeJson = (value: unknown): JsonValue => {
  if (value === null || value === undefined) {
    return null;
  }
  if (
    typeof value === "string" ||
    typeof value === "number" ||
    typeof value === "boolean"
  ) {
    return value;
  }
  if (Array.isArray(value)) {
    return value.map((entry) => normalizeJson(entry));
  }
  if (typeof value === "object") {
    const result: Record<string, JsonValue> = {};
    Object.entries(value as Record<string, unknown>).forEach(([key, entry]) => {
      result[key] = normalizeJson(entry);
    });
    return result;
  }
  return String(value);
};

const formatPrimitive = (value: JsonPrimitive) => {
  if (value === null) {
    return "null";
  }
  if (typeof value === "string") {
    const escaped = value.replace(/"/g, '\\"');
    return `"${escaped}"`;
  }
  return String(value);
};

const renderJsonNode = (
  value: JsonValue,
  path: string,
  label?: string,
  depth = 0,
): ReactElement => {
  if (Array.isArray(value)) {
    const title = label ?? "Array";
    return (
      <details key={path} className="run-detail__json-node" open={depth < 1}>
        <summary>
          <span className="run-detail__json-key">{title}</span>
          <span className="run-detail__json-meta">[{value.length}]</span>
        </summary>
        <div className="run-detail__json-children">
          {value.map((item, index) =>
            renderJsonNode(item, `${path}.${index}`, `[${index}]`, depth + 1),
          )}
        </div>
      </details>
    );
  }

  if (isRecord(value)) {
    const entries = Object.entries(value);
    const title = label ?? "Object";
    const metaLabel = `${entries.length} ${entries.length === 1 ? "key" : "keys"}`;
    return (
      <details key={path} className="run-detail__json-node" open={depth < 1}>
        <summary>
          <span className="run-detail__json-key">{title}</span>
          <span className="run-detail__json-meta">{metaLabel}</span>
        </summary>
        <div className="run-detail__json-children">
          {entries.map(([key, entry]) =>
            renderJsonNode(entry, `${path}.${key}`, key, depth + 1),
          )}
        </div>
      </details>
    );
  }

  const valueClass =
    value === null
      ? "run-detail__json-value--null"
      : typeof value === "string"
        ? "run-detail__json-value--string"
        : typeof value === "number"
          ? "run-detail__json-value--number"
          : "run-detail__json-value--boolean";

  return (
    <div key={path} className="run-detail__json-leaf">
      {label && <span className="run-detail__json-key">{label}:</span>}
      <code className={`run-detail__json-value ${valueClass}`}>
        {formatPrimitive(value)}
      </code>
    </div>
  );
};

const CollapsibleJsonView = ({ value }: { value: JsonValue }) => (
  <div className="run-detail__json-tree">
    {renderJsonNode(value, "root", undefined, 0)}
  </div>
);

export default CollapsibleJsonView;
