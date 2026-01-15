import { Link } from "react-router-dom";
import { useEffect, useMemo, useState } from "react";
import StatusBadge from "../components/StatusBadge";
import { getClientSessionId } from "../lib/clientSession";
import { useAuthStore } from "@store/authSlice";
import { useToolbarStore } from "../features/builder/hooks/useToolbar";
import { useRuns, useRunsStore } from "../store";
import { useTranslation } from "react-i18next";

export const RunsPage = () => {
  const { t, i18n } = useTranslation();
  const canViewRuns = useAuthStore((state) =>
    state.hasRole(["admin", "run.viewer", "workflow.editor"])
  );
  const [showMiddlewareOnly, setShowMiddlewareOnly] = useState(false);
  const [cancellingId, setCancellingId] = useState<string | null>(null);
  const { items: runs, status, error, refetch } = useRuns(undefined, { enabled: canViewRuns });
  const filteredRuns = useMemo(
    () =>
      showMiddlewareOnly
        ? runs.filter((run) =>
            (run.nodes ?? []).some((node) => {
              const meta = node.metadata as Record<string, unknown> | undefined;
              const mids = meta?.middlewares;
              if (!Array.isArray(mids) || mids.length === 0) {
                return false;
              }
              return mids.some((entry) => {
                if (typeof entry === "string") {
                  return entry.length > 0;
                }
                if (entry && typeof entry === "object") {
                  return typeof (entry as { id?: unknown }).id === "string";
                }
                return false;
              });
            })
          )
        : runs,
    [runs, showMiddlewareOnly]
  );
  const cancelRun = useRunsStore((state) => state.cancelRun);
  const setToolbar = useToolbarStore((state) => state.setContent);

  const toolbarContent = useMemo(() => {
    if (!canViewRuns) {
      return null;
    }
    return (
      <div className="toolbar-buttons">
        <button className="btn btn--ghost" type="button" onClick={() => refetch()}>
          <span className="btn__icon" aria-hidden="true">
            <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6">
              <path d="M4 4v4h4" />
              <path d="M16 16v-4h-4" />
              <path d="M4 12a6 6 0 0 0 9.9 3.5L16 12" />
              <path d="M16 8a6 6 0 0 0-9.9-3.5L4 8" />
            </svg>
          </span>
          {t("common.refresh")}
        </button>
      </div>
    );
  }, [canViewRuns, i18n.language, refetch, t]);

  useEffect(() => {
    setToolbar(toolbarContent);
    return () => setToolbar(null);
  }, [setToolbar, toolbarContent]);

  useEffect(() => {
    getClientSessionId();
  }, []);

  if (!canViewRuns) {
    return (
      <div className="card">
        <h2>{t("runs.title")}</h2>
        <p className="text-subtle">
          {t("runs.noPermission")} {t("runs.noPermissionDetail")}
        </p>
      </div>
    );
  }

  if (status === "loading") {
    return <p>{t("runs.loading")}</p>;
  }

  if (status === "error") {
    return (
      <div className="card">
        <p className="error">
          {t("runs.loadFailed", { message: (error as Error).message || t("common.unknownError") })}
        </p>
        <button onClick={() => refetch()} className="btn">
          {t("common.retry")}
        </button>
      </div>
    );
  }

  return (
    <div className="card">
      <header className="card__header">
        <div>
          <h2>{t("runs.title")}</h2>
          <p className="text-subtle">{t("runs.subtitle")}</p>
        </div>
        <div className="run-detail__toggle">
          <input
            id="middleware-filter"
            type="checkbox"
            checked={showMiddlewareOnly}
            onChange={(event) => setShowMiddlewareOnly(event.target.checked)}
          />
          <label htmlFor="middleware-filter">{t("runs.showMiddleware")}</label>
        </div>
      </header>
      {(showMiddlewareOnly ? filteredRuns : runs).length === 0 ? (
        <p>{t("runs.noRuns")}</p>
      ) : (
        <table className="data-table">
          <thead>
            <tr>
              <th>{t("runs.table.runId")}</th>
              <th>{t("runs.table.status")}</th>
              <th>{t("runs.table.clientId")}</th>
              <th>{t("runs.table.started")}</th>
              <th>{t("runs.table.finished")}</th>
              <th>{t("runs.table.actions")}</th>
            </tr>
          </thead>
          <tbody>
            {(showMiddlewareOnly ? filteredRuns : runs).map((run) => (
              <tr key={run.runId}>
                <td>
                  <Link to={`/runs/${run.runId}`} className="link">
                    {run.runId}
                  </Link>
                </td>
                <td>
                  <StatusBadge status={run.status} />
                </td>
                <td>{run.clientId ?? "-"}</td>
                <td>{run.startedAt ?? "-"}</td>
                <td>{run.finishedAt ?? "-"}</td>
                <td>
                  {run.status === "running" || run.status === "queued" ? (
                    <button
                      className="btn btn--ghost"
                      type="button"
                      onClick={async () => {
                        setCancellingId(run.runId);
                        try {
                          await cancelRun(run.runId);
                        } catch (mutationError) {
                          console.error("Failed to stop run", mutationError);
                        } finally {
                          setCancellingId(null);
                        }
                      }}
                      disabled={cancellingId === run.runId}
                    >
                      {t("runs.stop")}
                    </button>
                  ) : (
                    "-"
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
};

export default RunsPage;
