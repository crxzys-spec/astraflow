import { Link } from "react-router-dom";
import { useListRuns } from "../api/endpoints";
import StatusBadge from "../components/StatusBadge";

export const RunsPage = () => {
  const { data, isLoading, isError, error, refetch } = useListRuns();
  const runs = data?.data.items ?? [];

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

