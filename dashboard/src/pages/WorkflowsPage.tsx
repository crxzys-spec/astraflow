import { Link } from "react-router-dom";
import { useListWorkflows } from "../api/endpoints";
import { useAuthStore } from "../features/auth/store";

const WorkflowsPage = () => {
  const workflowsQuery = useListWorkflows(undefined, {
    query: {
      staleTime: 60_000
    }
  });
  const canCreateWorkflow = useAuthStore((state) => state.hasRole(["admin", "workflow.editor"]));

  const workflows = workflowsQuery.data?.data?.items ?? [];
  const isLoading = workflowsQuery.isLoading;
  const isError = workflowsQuery.isError;
  const errorMessage =
    (workflowsQuery.error as Error | undefined)?.message ??
    (workflowsQuery.error as { response?: { data?: { message?: string } } } | undefined)?.response
      ?.data?.message;

  return (
    <div className="card stack">
      <header className="card__header">
        <div>
          <h2>Workflows</h2>
          <p className="text-subtle">
            Browse workflow definitions and open them in the interactive builder.
          </p>
        </div>
        {canCreateWorkflow && (
          <Link className="btn btn--primary" to="/workflows/new">
            Create Workflow
          </Link>
        )}
      </header>

      {isLoading && (
        <div className="card card--surface">
          <p>Loading workflows...</p>
        </div>
      )}

      {isError && (
        <div className="card card--error">
          <p className="error">Unable to load workflows: {errorMessage ?? "Unknown error"}</p>
          <button className="btn" type="button" onClick={() => workflowsQuery.refetch()}>
            Retry
          </button>
        </div>
      )}

      {!isLoading && !isError && workflows.length === 0 && (
        <div className="card card--surface">
          <p>No workflows found. Use “Create Workflow” to start a new definition.</p>
        </div>
      )}

      {!isLoading && !isError && workflows.length > 0 && (
        <div className="card stack">
          {workflows.map((workflow) => {
            const metadata = workflow.metadata ?? { name: workflow.id, namespace: "default" };
            const tags = metadata.tags ?? [];
            const namespace = metadata.namespace ?? "default";
            const description = metadata.description ?? "No description provided.";
            const ownerId = metadata.ownerId ?? metadata.createdBy ?? null;
            const createdBy = metadata.createdBy ?? null;
            const updatedBy = metadata.updatedBy ?? null;
            return (
              <div key={workflow.id} className="card card--surface workflow-card">
                <div className="workflow-card__header">
                  <div>
                    <h3>{metadata.name ?? workflow.id}</h3>
                    <p className="text-subtle">{description}</p>
                  </div>
                  <div className="workflow-card__actions">
                    <span className="badge">{namespace}</span>
                    <Link className="btn" to={`/workflows/${workflow.id}`}>
                      Open Builder
                    </Link>
                  </div>
                </div>
                <div className="workflow-card__meta">
                  <div>
                    <strong>ID:</strong> <code>{workflow.id}</code>
                  </div>
                  {ownerId && (
                    <div>
                      <strong>Owner:</strong> {ownerId}
                    </div>
                  )}
                  {createdBy && (
                    <div>
                      <strong>Created by:</strong> {createdBy}
                    </div>
                  )}
                  {updatedBy && updatedBy !== createdBy && (
                    <div>
                      <strong>Updated by:</strong> {updatedBy}
                    </div>
                  )}
                  <div>
                    <strong>Nodes:</strong> {workflow.nodes?.length ?? 0}
                  </div>
                  {tags.length > 0 && (
                    <div className="workflow-card__tags">
                      {tags.map((tag) => (
                        <span key={tag} className="chip">
                          {tag}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default WorkflowsPage;
