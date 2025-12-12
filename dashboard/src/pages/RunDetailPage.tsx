import { Link, useNavigate, useParams } from "react-router-dom";
import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import { useGetRun, useGetRunDefinition } from "../api/endpoints";
import { getClientSessionId } from "../lib/clientSession";
import StatusBadge from "../components/StatusBadge";
import CollapsibleJsonView, {
  normalizeJson,
  type JsonValue,
} from "../components/CollapsibleJsonView";
import { useRunSseSync } from "../hooks/useRunSseSync";
import { useRunDetailData } from "../hooks/useRunDetailData";
import { MiddlewareTraceList, NodeGroups, RunSummary } from "./RunDetailSections";

type DetailPanel = "run" | "workflow";

interface RunDetailPageProps {
  runIdOverride?: string;
  onClose?: () => void;
}

export const RunDetailPage = ({ runIdOverride, onClose }: RunDetailPageProps = {}) => {
  const params = useParams<{ runId: string }>();
  const routeRunId = params?.runId;
  const runId = runIdOverride ?? routeRunId;
  const navigate = useNavigate();
  const [activePanel, setActivePanel] = useState<DetailPanel>("run");
  const [showMiddlewareOnly, setShowMiddlewareOnly] = useState(false);
  const [copyStatus, setCopyStatus] = useState<"idle" | "copied" | "error">("idle");

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

  const workflowDefinition = (definitionQuery.data as any)?.data ?? definitionQuery.data;
  const workflowLink = workflowDefinition?.id;
  const runData = runQuery.data;

  const {
    middlewareRelations,
    nodeGroups,
    middlewareTraces,
  } = useRunDetailData({
    runData,
    workflowDefinition,
    showMiddlewareOnly,
  });

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

  useRunSseSync({
    activeRunId: runId,
    activeRunStatus: runData?.status,
    enabled: Boolean(runId),
  });

  useEffect(() => {
    setCopyStatus("idle");
  }, [activePanel, workflowDefinition?.id, runData?.runId]);

  const handleClose = useCallback(() => {
    if (onClose) {
      onClose();
    } else {
      navigate(-1);
    }
  }, [navigate, onClose]);

  let modalContent: ReactNode = null;

  if (!runId) {
    modalContent = (
      <div className="run-detail__status">
        <p className="error">Missing run identifier.</p>
        <button className="btn btn--ghost" type="button" onClick={handleClose}>
          Close
        </button>
      </div>
    );
  } else if (runQuery.isLoading) {
    modalContent = (
      <div className="run-detail__status">
        <p>Loading run...</p>
      </div>
    );
  } else if (runQuery.isError) {
    modalContent = (
      <div className="run-detail__status">
        <p className="error">Failed to load run: {(runQuery.error as Error).message}</p>
        <button className="btn btn--ghost" type="button" onClick={handleClose}>
          Close
        </button>
      </div>
    );
  } else if (!runData) {
    modalContent = (
      <div className="run-detail__status">
        <p>No details available.</p>
        <button className="btn btn--ghost" type="button" onClick={handleClose}>
          Close
        </button>
      </div>
    );
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

  if (!modalContent && runData) {
    modalContent = (
      <div className="run-detail">
        <div className="run-detail__layout">
          <div className="card run-detail__primary">
            <button
              type="button"
              className="run-detail__back"
              onClick={handleClose}
            >
              <span className="run-detail__back-icon" aria-hidden="true">
                &larr;
              </span>
              <span className="run-detail__back-label">Back</span>
            </button>
            <header className="card__header">
              <div>
                <h2>{runData.runId}</h2>
                <p className="text-subtle">Client: {runData.clientId ?? "-"}</p>
              </div>
              <StatusBadge status={runData.status} />
            </header>

            <div className="run-detail__primary-scroll">
              <RunSummary runData={runData} workflowLink={workflowLink} />
              {nodeGroups.length > 0 && (
                <div className="run-detail__nodes">
                  <h3>Node Status</h3>
                  <label className="run-detail__toggle">
                    <input
                      type="checkbox"
                      checked={showMiddlewareOnly}
                      onChange={(event) => setShowMiddlewareOnly(event.target.checked)}
                    />
                    <span>Show middleware hosts/middlewares only</span>
                  </label>
                  <MiddlewareTraceList traces={middlewareTraces} />
                  <NodeGroups
                    nodeGroups={nodeGroups}
                    middlewareRelations={middlewareRelations}
                  />
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
  }

  return (
    <div className="run-detail-modal" role="dialog" aria-modal="true">
      <div className="run-detail-modal__backdrop" onClick={handleClose} />
      <div className="run-detail-modal__panel">
        {modalContent}
      </div>
    </div>
  );
};

export default RunDetailPage;
