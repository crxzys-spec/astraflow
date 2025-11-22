import { Link } from "react-router-dom";
import { useEffect, useMemo } from "react";
import { useListRuns } from "../api/endpoints";
import StatusBadge from "../components/StatusBadge";
import { sseClient } from "../lib/sseClient";
import { UiEventType } from "../api/models/uiEventType";
import { getClientSessionId } from "../lib/clientSession";
import { useQueryClient } from "@tanstack/react-query";
import type { RunStatusEvent } from "../api/models/runStatusEvent";
import type { RunSnapshotEvent } from "../api/models/runSnapshotEvent";
import { replaceRunSnapshot, updateRunCaches } from "../lib/sseCache";
import { useAuthStore } from "../features/auth/store";
import { useToolbarStore } from "../features/workflow/hooks/useToolbar";

export const RunsPage = () => {
  const canViewRuns = useAuthStore((state) =>
    state.hasRole(["admin", "run.viewer", "workflow.editor"])
  );
  const { data, isLoading, isError, error, refetch } = useListRuns(undefined, {
    query: { enabled: canViewRuns }
  });
  const runs = data?.data.items ?? [];
  const queryClient = useQueryClient();
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
          Refresh
        </button>
      </div>
    );
  }, [canViewRuns, refetch]);

  useEffect(() => {
    setToolbar(toolbarContent);
    return () => setToolbar(null);
  }, [setToolbar, toolbarContent]);

  useEffect(() => {
    getClientSessionId();
  }, []);

  useEffect(() => {
    if (!canViewRuns) {
      return;
    }
    const unsubscribe = sseClient.subscribe((event) => {
      if (event.type === UiEventType.runstatus && event.data?.kind === "run.status") {
        const payload = event.data as RunStatusEvent;
        const runId = payload.runId;
        updateRunCaches(queryClient, runId, (run) => {
          if (run.runId !== runId) {
            return run;
          }
          const next = { ...run, status: payload.status };
          if (payload.startedAt !== undefined) {
            next.startedAt = payload.startedAt ?? null;
          }
          if (payload.finishedAt !== undefined) {
            next.finishedAt = payload.finishedAt ?? null;
          }
          return next;
        });
      } else if (
        event.type === UiEventType.runsnapshot &&
        event.data?.kind === "run.snapshot" &&
        event.data.run?.runId
      ) {
        const snapshot = event.data as RunSnapshotEvent;
        const runId = snapshot.run.runId;
        const combinedRun = {
          ...snapshot.run,
          nodes: snapshot.nodes ?? snapshot.run.nodes,
        };
        replaceRunSnapshot(queryClient, runId, combinedRun);
      }
    });

    return () => unsubscribe();
  }, [queryClient, canViewRuns]);

  if (!canViewRuns) {
    return (
      <div className="card">
        <h2>Runs</h2>
        <p className="text-subtle">
          You do not have permission to view run telemetry. Please request the run.viewer or workflow.editor role.
        </p>
      </div>
    );
  }

  if (isLoading) {
    return <p>Loading runs...</p>;
  }

  if (isError) {
    return (
      <div className="card">
        <p className="error">Failed to load runs: {(error as Error).message}</p>
        <button onClick={() => refetch()} className="btn">Retry</button>
      </div>
    );
  }

  return (
    <div className="card">
      <header className="card__header">
        <div>
          <h2>Runs</h2>
          <p className="text-subtle">Most recent execution attempts</p>
        </div>
      </header>
      {runs.length === 0 ? (
        <p>No runs yet.</p>
      ) : (
        <table className="data-table">
          <thead>
            <tr>
              <th>Run ID</th>
              <th>Status</th>
              <th>Client ID</th>
              <th>Started</th>
              <th>Finished</th>
            </tr>
          </thead>
          <tbody>
            {runs.map((run) => (
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
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
};

export default RunsPage;
