import { Link, useNavigate, useParams } from "react-router-dom";
import { useGetRun, useGetRunDefinition } from "../api/endpoints";
import StatusBadge from "../components/StatusBadge";

export const RunDetailPage = () => {
  const { runId } = useParams<{ runId: string }>();
  const navigate = useNavigate();

  if (!runId) {
    return <p className="error">Missing run identifier.</p>;
  }

  const runQuery = useGetRun(runId);
  const definitionQuery = useGetRunDefinition(runId, {
    query: {
      enabled: runQuery.isSuccess
    }
  });

  if (runQuery.isLoading) {
    return <p>Loading run...</p>;
  }

  if (runQuery.isError) {
    return (
      <div className="card">
        <p className="error">Failed to load run: {(runQuery.error as Error).message}</p>
        <button className="btn" onClick={() => navigate(-1)}>Back</button>
      </div>
    );
  }

  const run = runQuery.data?.data;

  if (!run) {
    return <p>No details available.</p>;
  }

  const workflowDefinition = definitionQuery.data?.data;
  const workflowLink = workflowDefinition?.id;
  const durationMs = (() => {
    if (!run.startedAt || !run.finishedAt) {
      return undefined;
    }
    const start = Date.parse(run.startedAt);
    const end = Date.parse(run.finishedAt);
    if (Number.isNaN(start) || Number.isNaN(end)) {
      return undefined;
    }
    return Math.max(end - start, 0);
  })();

  return (
    <div className="stack">
      <div className="card">
        <button className="link" onClick={() => navigate(-1)}>&larr; Back</button>
        <header className="card__header">
          <div>
            <h2>{run.runId}</h2>
            <p className="text-subtle">Client: {run.clientId ?? "-"}</p>
          </div>
          <StatusBadge status={run.status} />
        </header>
        <dl className="data-grid">
          <div>
            <dt>Started</dt>
            <dd>{run.startedAt ?? "-"}</dd>
          </div>
          <div>
            <dt>Finished</dt>
            <dd>{run.finishedAt ?? "-"}</dd>
          </div>
          <div>
            <dt>Duration (ms)</dt>
            <dd>{durationMs ?? "-"}</dd>
          </div>
          <div>
            <dt>Definition Hash</dt>
            <dd>{run.definitionHash}</dd>
          </div>
          <div>
            <dt>Workflow Definition</dt>
            <dd>{workflowLink ?? "-"}</dd>
          </div>
        </dl>
      </div>

      <div className="card">
        <header className="card__header">
          <h3>Run Payload</h3>
        </header>
        <pre className="code-block">{JSON.stringify(run, null, 2)}</pre>
      </div>

      {workflowDefinition && (
        <div className="card">
          <header className="card__header">
          <h3>Workflow Definition</h3>
          {workflowLink ? (
            <Link to={`/workflows/${workflowLink}`} className="link">
              Open Workflow
            </Link>
          ) : (
            <span className="text-subtle">No linked workflow</span>
          )}
        </header>
          <pre className="code-block">{JSON.stringify(workflowDefinition, null, 2)}</pre>
        </div>
      )}
    </div>
  );
};

export default RunDetailPage;


