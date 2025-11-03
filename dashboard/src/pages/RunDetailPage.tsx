import { Link, useNavigate, useParams } from "react-router-dom";
import { useEffect, useMemo, useState, type ReactElement } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useGetRun, useGetRunDefinition } from "../api/endpoints";
import { UiEventType } from "../api/models/uiEventType";
import type { RunStatusEvent } from "../api/models/runStatusEvent";
import type { RunSnapshotEvent } from "../api/models/runSnapshotEvent";
import type { NodeStateEvent } from "../api/models/nodeStateEvent";
import type { NodeResultSnapshotEvent } from "../api/models/nodeResultSnapshotEvent";
import type { NodeErrorEvent } from "../api/models/nodeErrorEvent";
import { sseClient } from "../lib/sseClient";
import { getClientSessionId } from "../lib/clientSession";
import {
  applyRunDefinitionSnapshot,
  replaceRunSnapshot,
  updateRunCaches,
  updateRunDefinitionNodeState,
  updateRunNode,
} from "../lib/sseCache";
import StatusBadge from "../components/StatusBadge";

type DetailPanel = "run" | "workflow";
type JsonPrimitive = string | number | boolean | null;
type JsonValue =
  | JsonPrimitive
  | JsonValue[]
  | {
      [key: string]: JsonValue;
    };

const isRecord = (value: JsonValue): value is Record<string, JsonValue> =>
  typeof value === "object" && value !== null && !Array.isArray(value);

const normalizeJson = (value: unknown): JsonValue => {
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

const formatDurationMs = (
  startedAt?: string | null,
  finishedAt?: string | null,
) => {
  if (!startedAt || !finishedAt) {
    return undefined;
  }
  const start = Date.parse(startedAt);
  const end = Date.parse(finishedAt);
  if (Number.isNaN(start) || Number.isNaN(end) || end < start) {
    return undefined;
  }
  return end - start;
};

const DurationLabel = ({
  startedAt,
  finishedAt,
}: {
  startedAt?: string | null;
  finishedAt?: string | null;
}) => {
  const durationMs = useMemo(
    () => formatDurationMs(startedAt, finishedAt),
    [startedAt, finishedAt],
  );
  if (durationMs === undefined) {
    return <>-</>;
  }
  if (durationMs < 1000) {
    return <>{`${durationMs} ms`}</>;
  }
  const seconds = durationMs / 1000;
  return <>{`${seconds.toFixed(2)} s`}</>;
};

export const RunDetailPage = () => {
  const { runId } = useParams<{ runId: string }>();
  const navigate = useNavigate();
  const [activePanel, setActivePanel] = useState<DetailPanel>("run");
  const [copyStatus, setCopyStatus] = useState<"idle" | "copied" | "error">(
    "idle",
  );

  const runQueryEnabled = Boolean(runId);
  const runQuery = useGetRun(runId ?? "", {
    query: {
      enabled: runQueryEnabled,
    },
  });
  const definitionQuery = useGetRunDefinition(runId ?? "", {
    query: {
      enabled: runQueryEnabled && runQuery.isSuccess,
    },
  });

  const workflowDefinition = definitionQuery.data?.data;
  const workflowLink = workflowDefinition?.id;
  const runData = runQuery.data?.data;
  const queryClient = useQueryClient();

  const rawPayload = activePanel === "workflow" ? workflowDefinition : runData;
  const normalizedPayload = useMemo<JsonValue | undefined>(() => {
    if (rawPayload === undefined) {
      return undefined;
    }
    return normalizeJson(rawPayload);
  }, [rawPayload]);
  const serializedPayload = useMemo<string | undefined>(() => {
    if (rawPayload === undefined) {
      return undefined;
    }
    return typeof rawPayload === "string"
      ? rawPayload
      : JSON.stringify(rawPayload, null, 2);
  }, [rawPayload]);

  useEffect(() => {
    if (!workflowDefinition && activePanel === "workflow") {
      setActivePanel("run");
    }
  }, [workflowDefinition, activePanel]);

  useEffect(() => {
    // Ensure client session id exists even if this page is opened directly.
    getClientSessionId();
  }, []);

  useEffect(() => {
    if (!runId) {
      return;
    }

    const unsubscribe = sseClient.subscribe((event) => {
      if (event.scope?.runId !== runId) {
        return;
      }
      if (event.type === UiEventType.runstatus && event.data?.kind === "run.status") {
        const payload = event.data as RunStatusEvent;
        updateRunCaches(queryClient, runId, (run) => {
          if (run.runId !== payload.runId) {
            return run;
          }
          const next = { ...run, status: payload.status };
          if (payload.startedAt !== undefined) {
            next.startedAt = payload.startedAt ?? null;
          }
          if (payload.finishedAt !== undefined) {
            next.finishedAt = payload.finishedAt ?? null;
          }
          if (payload.status === "failed" && payload.reason) {
            const existingError =
              run.error && typeof run.error === "object" ? run.error : undefined;
            next.error = {
              code: existingError?.code ?? "run.failed",
              message: payload.reason,
              details: existingError?.details,
            };
          }
          return next;
        });
      } else if (
        event.type === UiEventType.runsnapshot &&
        event.data?.kind === "run.snapshot" &&
        event.data.run?.runId === runId
      ) {
        const snapshot = event.data as RunSnapshotEvent;
        replaceRunSnapshot(queryClient, runId, snapshot.run, snapshot.nodes ?? null);
        applyRunDefinitionSnapshot(queryClient, runId, snapshot.nodes ?? null);
      } else if (event.type === UiEventType.nodestate && event.data?.kind === "node.state") {
        const payload = event.data as NodeStateEvent;
        updateRunNode(queryClient, runId, payload.nodeId, (node) => {
          const next = { ...node };
          if (payload.state?.stage) {
            next.status = payload.state.stage as typeof node.status;
          }
          if (payload.state?.error !== undefined) {
            next.error = payload.state.error ?? null;
          }
          if (payload.state?.message !== undefined) {
            const base =
              next.metadata && typeof next.metadata === "object"
                ? { ...(next.metadata as Record<string, unknown>) }
                : {};
            if (payload.state.message === null) {
              delete (base as Record<string, unknown>).statusMessage;
              delete (base as Record<string, unknown>).message;
              next.metadata = Object.keys(base).length > 0 ? base : null;
            } else {
              (base as Record<string, unknown>).statusMessage = payload.state.message;
              (base as Record<string, unknown>).message = payload.state.message;
              next.metadata = base;
            }
          }
          if (payload.state) {
            next.state = {
              ...payload.state,
              stage: payload.state.stage ?? next.status,
            };
          } else {
            next.state = {
              ...(next.state ?? {}),
              stage: next.status,
            };
          }
          return next;
        });
        updateRunDefinitionNodeState(queryClient, runId, payload.nodeId, payload.state ?? undefined);
      } else if (
        event.type === UiEventType.noderesultsnapshot &&
        event.data?.kind === "node.result.snapshot"
      ) {
        const payload = event.data as NodeResultSnapshotEvent;
        updateRunNode(queryClient, runId, payload.nodeId, (node) => ({
          ...node,
          result: payload.content ?? null,
          artifacts: payload.artifacts ?? node.artifacts ?? null,
        }));
      } else if (event.type === UiEventType.nodeerror && event.data?.kind === "node.error") {
        const payload = event.data as NodeErrorEvent;
        updateRunNode(queryClient, runId, payload.nodeId, (node) => ({
          ...node,
          status: "failed",
          error: payload.error,
          state: {
            ...(node.state ?? {}),
            stage: "failed",
            error: payload.error,
          },
        }));
      }
    });

    return () => {
      unsubscribe();
    };
  }, [queryClient, runId]);

  useEffect(() => {
    setCopyStatus("idle");
  }, [activePanel, workflowDefinition?.id, runData?.runId]);

  if (!runId) {
    return <p className="error">Missing run identifier.</p>;
  }

  if (runQuery.isLoading) {
    return <p>Loading run...</p>;
  }

  if (runQuery.isError) {
    return (
      <div className="card">
        <p className="error">
          Failed to load run: {(runQuery.error as Error).message}
        </p>
        <button className="btn" onClick={() => navigate(-1)}>
          Back
        </button>
      </div>
    );
  }

  if (!runData) {
    return <p>No details available.</p>;
  }

  const displayPayload = normalizedPayload;
  const displayTitle =
    activePanel === "workflow" ? "Workflow Definition" : "Run Payload";
  const emptyStateMessage =
    activePanel === "workflow"
      ? "Workflow definition unavailable for this run."
      : "Run payload unavailable.";

  const handleCopyPayload = async () => {
    if (serializedPayload === undefined) {
      return;
    }
    if (
      !navigator.clipboard ||
      typeof navigator.clipboard.writeText !== "function"
    ) {
      setCopyStatus("error");
      return;
    }
    try {
      await navigator.clipboard.writeText(serializedPayload);
      setCopyStatus("copied");
    } catch {
      setCopyStatus("error");
    } finally {
      window.setTimeout(() => setCopyStatus("idle"), 2000);
    }
  };

  return (
    <div className="run-detail">
      <div className="run-detail__layout">
        <div className="card run-detail__primary">
          <button
            type="button"
            className="run-detail__back"
            onClick={() => navigate(-1)}
          >
            <span className="run-detail__back-icon" aria-hidden="true">
              &larr;
            </span>
            <span className="run-detail__back-label">Back</span>
          </button>
          <header className="card__header">
            <div>
              <h2>{runData?.runId}</h2>
              <p className="text-subtle">Client: {runData?.clientId ?? "-"}</p>
            </div>
            <StatusBadge status={runData?.status} />
          </header>

          <div className="run-detail__primary-scroll">
            <div className="run-detail__meta-grid">
              <div className="run-detail__meta-item">
                <span className="run-detail__meta-label">Started</span>
                <span className="run-detail__meta-value">
                  {runData?.startedAt ?? "-"}
                </span>
              </div>
              <div className="run-detail__meta-item">
                <span className="run-detail__meta-label">Finished</span>
                <span className="run-detail__meta-value">
                  {runData?.finishedAt ?? "-"}
                </span>
              </div>
              <div className="run-detail__meta-item">
                <span className="run-detail__meta-label">Duration</span>
                <span className="run-detail__meta-value">
                  <DurationLabel
                    startedAt={runData?.startedAt}
                    finishedAt={runData?.finishedAt}
                  />
                </span>
              </div>
            </div>
            <div className="run-detail__meta-inline">
              <span className="run-detail__meta-label">Definition Hash:</span>
              <code className="run-detail__meta-inline-code">
                {runData?.definitionHash ?? "-"}
              </code>
            </div>
            <div className="run-detail__meta-inline">
              <span className="run-detail__meta-label">
                Workflow Definition:
              </span>
              <code className="run-detail__meta-inline-code">
                {workflowLink ?? "-"}
              </code>
            </div>

            {runData?.error && (
              <div className="run-detail__section">
                <h4>Run Error</h4>
                <pre className="run-detail__payload">
                  {JSON.stringify(runData?.error, null, 2)}
                </pre>
              </div>
            )}

            {runData?.nodes && runData?.nodes.length > 0 && (
              <div className="run-detail__nodes">
                <h3>Node Status</h3>
                <div className="run-detail__nodes-grid">
                  {runData?.nodes.map((node) => (
                    <div key={node.nodeId} className="run-detail__node-card">
                      <header>
                        <span className="run-detail__node-id">
                          {node.nodeId}
                        </span>
                        {node.status && <StatusBadge status={node.status} />}
                      </header>
                      <dl>
                        <div>
                          <dt>Task</dt>
                          <dd>{node.taskId ?? "-"}</dd>
                        </div>
                        <div>
                          <dt>Worker</dt>
                          <dd>{node.workerId ?? "-"}</dd>
                        </div>
                        <div>
                          <dt>Started</dt>
                          <dd>{node.startedAt ?? "-"}</dd>
                        </div>
                        <div>
                          <dt>Finished</dt>
                          <dd>{node.finishedAt ?? "-"}</dd>
                        </div>
                        {node.state?.message && (
                          <div>
                            <dt>Message</dt>
                            <dd>{node.state.message}</dd>
                          </div>
                        )}
                        {typeof node.state?.progress === "number" && (
                          <div>
                            <dt>Progress</dt>
                            <dd>{`${Math.round((node.state.progress ?? 0) * 100)}%`}</dd>
                          </div>
                        )}
                        {node.state?.lastUpdatedAt && (
                          <div>
                            <dt>Updated</dt>
                            <dd>{node.state.lastUpdatedAt}</dd>
                          </div>
                        )}
                      </dl>
                    {node.error && (
                        <details className="run-detail__node-section">
                          <summary>Error</summary>
                          <pre className="run-detail__payload">
                            {JSON.stringify(node.error, null, 2)}
                          </pre>
                        </details>
                      )}
                      {node.result && Object.keys(node.result).length > 0 && (
                        <details className="run-detail__node-section">
                          <summary>Result</summary>
                          <pre className="run-detail__payload">
                            {JSON.stringify(node.result, null, 2)}
                          </pre>
                        </details>
                      )}
                      {node.artifacts && node.artifacts.length > 0 && (
                        <details className="run-detail__node-section">
                          <summary>Artifacts</summary>
                          <pre className="run-detail__payload">
                            {JSON.stringify(node.artifacts, null, 2)}
                          </pre>
                        </details>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        <div className="run-detail__side">
          <div className="run-detail__panel">
            <div className="run-detail__panel-toggle">
              <button
                type="button"
                className={`run-detail__toggle-btn ${activePanel === "run" ? "run-detail__toggle-btn--active" : ""}`}
                onClick={() => setActivePanel("run")}
                aria-pressed={activePanel === "run"}
              >
                Run Payload
              </button>
              <button
                type="button"
                className={`run-detail__toggle-btn ${activePanel === "workflow" ? "run-detail__toggle-btn--active" : ""}`}
                onClick={() => setActivePanel("workflow")}
                aria-pressed={activePanel === "workflow"}
                disabled={!workflowDefinition}
              >
                Workflow Definition
              </button>
            </div>

            <div className="card run-detail__payload-card">
              <header className="card__header">
                <h3>{displayTitle}</h3>
                {activePanel === "workflow" && workflowLink ? (
                  <Link to={`/workflows/${workflowLink}`} className="link">
                    Open Workflow
                  </Link>
                ) : null}
              </header>
              {displayPayload !== undefined ? (
                <>
                  <div className="run-detail__payload-tree">
                    <CollapsibleJsonView value={displayPayload} />
                  </div>
                  <div className="run-detail__payload-actions">
                    <button
                      type="button"
                      className="run-detail__payload-copy"
                      onClick={handleCopyPayload}
                    >
                      {copyStatus === "copied"
                        ? "Copied"
                        : copyStatus === "error"
                          ? "Copy Failed"
                          : "Copy"}
                    </button>
                  </div>
                </>
              ) : (
                <p className="text-subtle run-detail__empty">
                  {emptyStateMessage}
                </p>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default RunDetailPage;

