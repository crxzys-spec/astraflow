import { useQueryClient } from "@tanstack/react-query";
import { useCancelRun, useListRuns } from "../../../api/endpoints";
import { updateRunCaches } from "../../../lib/sseCache";
import StatusBadge from "../../../components/StatusBadge";
import { useAuthStore } from "../../auth/store";

interface RunsInspectorPanelProps {
  onSelectRun: (runId: string) => void;
}

const RunsInspectorPanel = ({ onSelectRun }: RunsInspectorPanelProps) => {
  const canViewRuns = useAuthStore((state) =>
    state.hasRole(["admin", "run.viewer", "workflow.editor"])
  );
  const queryClient = useQueryClient();
  const cancelRun = useCancelRun(
    {
      mutation: {
        onSuccess: (_result, variables) => {
          const runId = variables?.runId;
          if (runId) {
            updateRunCaches(queryClient, runId, (run) =>
              run.runId === runId ? { ...run, status: "cancelled" } : run
            );
          }
        }
      }
    },
    queryClient
  );
  const { data, isLoading, isError, error, refetch } = useListRuns(undefined, {
    query: {
      enabled: canViewRuns,
      refetchInterval: false,
    }
  });
  const runs = data?.items ?? [];

  if (!canViewRuns) {
    return (
      <div className="inspector-panel__empty">
        <p>You do not have permission to view runs.</p>
      </div>
    );
  }

  if (isLoading) {
    return <div className="inspector-panel__loading">Loading runs...</div>;
  }

  if (isError) {
    return (
      <div className="inspector-panel__empty">
        <p>Failed to load runs: {(error as Error).message}</p>
        <button className="btn btn--ghost" type="button" onClick={() => refetch()}>
          Retry
        </button>
      </div>
    );
  }

  if (!runs.length) {
    return (
      <div className="inspector-panel__empty">
        <p>No runs yet.</p>
        <button className="btn btn--ghost" type="button" onClick={() => refetch()}>
          Refresh
        </button>
      </div>
    );
  }

  return (
    <div className="runs-panel">
      <div className="runs-panel__header">
        <div>
          <h4>Recent runs</h4>
          <p className="text-subtle">Latest execution attempts</p>
        </div>
        <button className="btn btn--ghost runs-panel__refresh" type="button" onClick={() => refetch()}>
          Refresh
        </button>
      </div>
      <div className="runs-panel__list">
        {runs.map((run) => {
          const isCancelable = run.status === "running" || run.status === "queued";
          const isCancelling = cancelRun.isPending && cancelRun.variables?.runId === run.runId;
          return (
            <div
              key={run.runId}
              className="runs-panel__item"
              role="button"
              tabIndex={0}
              onClick={() => onSelectRun(run.runId)}
              onKeyDown={(event) => {
                if (event.key === "Enter" || event.key === " ") {
                  event.preventDefault();
                  onSelectRun(run.runId);
                }
              }}
            >
              <div className="runs-panel__identity">
                <p className="runs-panel__run-id">{run.runId}</p>
                <p className="runs-panel__meta">Client {run.clientId ?? "-"}</p>
              </div>
              <div className="runs-panel__status">
                <StatusBadge status={run.status} />
                <span>{run.startedAt ?? "Pending"}</span>
              </div>
              {isCancelable && (
                <button
                  type="button"
                  className="btn btn--ghost runs-panel__stop"
                  onClick={(event) => {
                    event.stopPropagation();
                    cancelRun.mutate(
                      { runId: run.runId },
                      { onError: (mutationError) => console.error("Failed to stop run", mutationError) }
                    );
                  }}
                  disabled={isCancelling}
                >
                  {isCancelling ? "Stopping..." : "Stop"}
                </button>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default RunsInspectorPanel;
