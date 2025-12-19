import { useMemo } from "react";
import StatusBadge from "../components/StatusBadge";
import { middlewareNextErrorMessages } from "../features/builder/middlewareErrors";
import type { MiddlewareTrace } from "../lib/middlewareTrace";
import type {
  MiddlewareRelations,
  NodeGroup,
  NodeWithFrame,
} from "../hooks/useRunDetailData";
import type { RunModel } from "../services/runs";

const DurationLabel = ({
  startedAt,
  finishedAt,
}: {
  startedAt?: string | null;
  finishedAt?: string | null;
}) => {
  const durationMs = useMemo(() => {
    if (!startedAt || !finishedAt) {
      return undefined;
    }
    const start = Date.parse(startedAt);
    const end = Date.parse(finishedAt);
    if (Number.isNaN(start) || Number.isNaN(end) || end < start) {
      return undefined;
    }
    return end - start;
  }, [startedAt, finishedAt]);

  if (durationMs === undefined) {
    return <>-</>;
  }
  if (durationMs < 1000) {
    return <>{`${durationMs} ms`}</>;
  }
  const seconds = durationMs / 1000;
  return <>{`${seconds.toFixed(2)} s`}</>;
};

export const RunSummary = ({
  runData,
  workflowLink,
}: {
  runData: RunModel;
  workflowLink?: string | null;
}) => (
  <>
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
  </>
);

const NodeCard = ({
  node,
  frame,
  middlewareRelations,
}: NodeWithFrame & { middlewareRelations: MiddlewareRelations }) => {
  const scopeLabel =
    frame?.aliasChain && frame.aliasChain.length > 0
      ? frame.aliasChain.join(" / ")
      : frame?.frameId ?? frame?.subgraphId;

  return (
    <div className="run-detail__node-card">
      <header>
        <span className="run-detail__node-id">{node.nodeId}</span>
        {node.status && <StatusBadge status={node.status} />}
      </header>
      <dl>
        <div>
          <dt>Task</dt>
          <dd>{node.taskId ?? "-"}</dd>
        </div>
        {middlewareRelations.roleByNode[node.nodeId] && (
          <div>
            <dt>Role</dt>
            <dd>{middlewareRelations.roleByNode[node.nodeId]}</dd>
          </div>
        )}
        {middlewareRelations.hostByMiddleware[node.nodeId] && (
          <div>
            <dt>Host</dt>
            <dd>{middlewareRelations.hostByMiddleware[node.nodeId]}</dd>
          </div>
        )}
        {middlewareRelations.chainByHost[node.nodeId]?.length ? (
          <div>
            <dt>Middlewares</dt>
            <dd className="run-detail__pill-row">
              {middlewareRelations.chainByHost[node.nodeId].map((mw) => (
                <span key={mw.id} className="run-detail__pill" title={mw.id}>
                  {mw.label || mw.id}
                </span>
              ))}
            </dd>
          </div>
        ) : null}
        {scopeLabel && (
          <div>
            <dt>Scope</dt>
            <dd>{scopeLabel}</dd>
          </div>
        )}
        {frame?.containerNodeId && (
          <div>
            <dt>Container</dt>
            <dd>{frame.containerNodeId}</dd>
          </div>
        )}
        <div>
          <dt>Worker</dt>
          <dd>{node.workerName ?? "-"}</dd>
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
            {JSON.stringify(
              {
                ...node.error,
                message:
                  node.error.code && middlewareNextErrorMessages[node.error.code]
                    ? middlewareNextErrorMessages[node.error.code]
                    : node.error.message,
              },
              null,
              2,
            )}
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
  );
};

export const NodeGroups = ({
  nodeGroups,
  middlewareRelations,
}: {
  nodeGroups: NodeGroup[];
  middlewareRelations: MiddlewareRelations;
}) => (
  <>
    {nodeGroups.map((group) => (
      <section key={group.key} className="run-detail__nodes-section">
        <div className="run-detail__nodes-section-header">
          <h4 className="run-detail__nodes-section-title">{group.label}</h4>
          {group.description && (
            <p className="run-detail__nodes-section-description">
              {group.description}
            </p>
          )}
        </div>
        <div className="run-detail__nodes-grid">
          {group.nodes.map(({ node, frame }) => (
            <NodeCard
              key={node.taskId ?? node.nodeId}
              node={node}
              frame={frame}
              middlewareRelations={middlewareRelations}
            />
          ))}
        </div>
      </section>
    ))}
  </>
);

export const MiddlewareTraceList = ({ traces }: { traces: MiddlewareTrace[] }) => {
  if (!traces.length) {
    return null;
  }
  return (
    <div className="run-detail__trace">
      <h4>Middleware Chains</h4>
      <div className="run-detail__trace-grid">
        {traces.map((trace) => (
          <div key={trace.hostId} className="run-detail__trace-card">
            <div className="run-detail__trace-host">
              <span className="run-detail__pill">Host: {trace.hostId}</span>
              {typeof trace.totalDurationMs === "number" && (
                <span className="run-detail__trace-total">
                  Total: {Math.round(trace.totalDurationMs)} ms
                </span>
              )}
            </div>
            <ol className="run-detail__trace-chain">
              {trace.nodes.map((entry, index) => (
                <li key={`${trace.hostId}-${entry.nodeId}-${index}`}>
                  <div className="run-detail__trace-node">
                    <span
                      className="run-detail__pill"
                      title={`#${index + 1} in chain`}
                    >
                      <span className="run-detail__pill-index">{index + 1}</span>
                      {entry.nodeId}
                    </span>
                    {entry.status && <StatusBadge status={entry.status} />}
                    <span className="run-detail__trace-meta">
                      {entry.startedAt || entry.finishedAt
                        ? `${entry.startedAt ?? "-"} -> ${entry.finishedAt ?? "-"}`
                        : ""}
                      {typeof entry.durationMs === "number"
                        ? ` (${Math.round(entry.durationMs)} ms)`
                        : ""}
                    </span>
                  </div>
                </li>
              ))}
            </ol>
          </div>
        ))}
      </div>
    </div>
  );
};
