import { Link } from "react-router-dom";
import { useEffect } from "react";
import { useListRuns } from "../api/endpoints";
import StatusBadge from "../components/StatusBadge";
import { sseClient } from "../lib/sseClient";
import { UiEventType } from "../api/models/uiEventType";
import { getClientSessionId } from "../lib/clientSession";
import { useQueryClient } from "@tanstack/react-query";
import type { RunStatusEvent } from "../api/models/runStatusEvent";
import type { RunSnapshotEvent } from "../api/models/runSnapshotEvent";
import { replaceRunSnapshot, updateRunCaches } from "../lib/sseCache";

export const RunsPage = () => {
  const { data, isLoading, isError, error, refetch } = useListRuns();
  const runs = data?.data.items ?? [];
  const queryClient = useQueryClient();

  useEffect(() => {
    getClientSessionId();
  }, []);

  useEffect(() => {
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
  }, [queryClient]);

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
        <button className="btn" onClick={() => refetch()}>Refresh</button>
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
