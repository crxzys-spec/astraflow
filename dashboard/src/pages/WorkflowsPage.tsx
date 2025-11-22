import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useDeleteWorkflow, useListWorkflows } from "../api/endpoints";
import { useAuthStore } from "../features/auth/store";
import { useToolbarStore } from "../features/workflow/hooks/useToolbar";

const WorkflowsPage = () => {
  const workflowsQuery = useListWorkflows(undefined, {
    query: {
      staleTime: 60_000
    }
  });
  const canCreateWorkflow = useAuthStore((state) => state.hasRole(["admin", "workflow.editor"]));
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [deletingWorkflowId, setDeletingWorkflowId] = useState<string | null>(null);
  const deleteWorkflowMutation = useDeleteWorkflow();

  const workflows = workflowsQuery.data?.data?.items ?? [];
  const isLoading = workflowsQuery.isLoading;
  const isError = workflowsQuery.isError;
  const errorMessage =
    (workflowsQuery.error as Error | undefined)?.message ??
    (workflowsQuery.error as { response?: { data?: { message?: string } } } | undefined)?.response
      ?.data?.message;

  const setToolbar = useToolbarStore((state) => state.setContent);

  const toolbarContent = useMemo(() => {
    if (!canCreateWorkflow) {
      return null;
    }
    return (
      <div className="toolbar-buttons">
        <Link className="btn btn--primary" to="/workflows/new">
          <span className="btn__icon" aria-hidden="true">
            <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6">
              <path d="M10 4v12" />
              <path d="M4 10h12" />
            </svg>
          </span>
          Create
        </Link>
      </div>
    );
  }, [canCreateWorkflow]);

  useEffect(() => {
    setToolbar(toolbarContent);
    return () => setToolbar(null);
  }, [toolbarContent, setToolbar]);

  const handleDelete = async (workflowId: string, workflowName: string) => {
    if (!window.confirm(`Delete workflow "${workflowName}"? This action can be undone by re-saving.`)) {
      return;
    }
    setDeleteError(null);
    setDeletingWorkflowId(workflowId);
    try {
      await deleteWorkflowMutation.mutateAsync({ workflowId });
      await workflowsQuery.refetch();
    } catch (error) {
      const defaultMessage = "Failed to delete workflow.";
      const responseMessage =
        (error as { response?: { data?: { message?: string } } })?.response?.data?.message;
      setDeleteError(responseMessage ?? (error as Error | undefined)?.message ?? defaultMessage);
    } finally {
      setDeletingWorkflowId(null);
    }
  };

  return (
    <div className="card stack store-panel">
      <header className="card__header">
        <div>
          <h2>Workflows</h2>
          <p className="text-subtle">
            Browse workflow definitions and open them in the interactive builder.
          </p>
        </div>
      </header>
      <div className="store-content">
      {deleteError && (
        <div className="card card--error">
          <p className="error">Unable to delete workflow: {deleteError}</p>
        </div>
      )}
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
        <div className="workflow-grid-shell">
          <div className="workflow-grid">
            {workflows.map((workflow) => {
            const metadata = workflow.metadata ?? { name: workflow.id, namespace: "default" };
            const tags = metadata.tags ?? [];
            const namespace = metadata.namespace ?? "default";
            const description = metadata.description ?? "No description provided.";
            const ownerDisplay = metadata.ownerName ?? metadata.ownerId ?? "Unassigned";
            const environment = metadata.environment ?? "default";
            const previewImage = workflow.previewImage ?? null;
            return (
              <article key={workflow.id} className="card card--surface workflow-card workflow-card--accent">
                <div className="workflow-card__media">
                  <div
                    className={`workflow-card__preview ${
                      previewImage ? "" : "workflow-card__preview--empty"
                    }`}
                  >
                    {previewImage ? (
                      <img
                        src={previewImage}
                        alt={`${metadata.name ?? workflow.id} preview`}
                        loading="lazy"
                      />
                    ) : (
                      <div className="workflow-card__preview-placeholder">Snapshot pending</div>
                    )}
                  </div>
                  <header className="workflow-card__header">
                    <div className="workflow-card__identity">
                      <small className="workflow-card__eyebrow">Workflow</small>
                      <h3>{metadata.name ?? workflow.id}</h3>
                      <p className="workflow-card__owner">@{ownerDisplay}</p>
                    </div>
                  </header>
                </div>
                <div className="workflow-card__body">
                  <p className="workflow-card__description">{description}</p>
                  <div className="workflow-card__chips workflow-card__chips--body">
                    <span className="chip chip--ghost">{namespace}</span>
                    <span className="chip chip--ghost">{environment}</span>
                  </div>
                  <div className="workflow-card__actions-row">
                    <div className="workflow-card__action-buttons">
                      <button
                        className="btn btn--ghost"
                        type="button"
                        disabled={deletingWorkflowId === workflow.id || deleteWorkflowMutation.isPending}
                        onClick={() => handleDelete(workflow.id, metadata.name ?? workflow.id)}
                      >
                        <span className="btn__icon" aria-hidden="true">🗑</span>
                        {deletingWorkflowId === workflow.id ? "Deleting..." : "Delete"}
                      </button>
                      <Link className="btn btn--primary" to={`/workflows/${workflow.id}`}>
                        <span className="btn__icon" aria-hidden="true">⟲</span>
                        Open Builder
                      </Link>
                    </div>
                  </div>
                  <footer className="workflow-card__footer">
                    {tags.length > 0 ? (
                      <div className="workflow-card__tags">
                        {tags.map((tag) => (
                          <span key={tag} className="chip">
                            {tag}
                          </span>
                        ))}
                      </div>
                    ) : <span />}
                    <div className="workflow-card__signature">
                      <span>Workflow ID</span>
                      <code>{workflow.id}</code>
                    </div>
                  </footer>
                </div>
              </article>
            );
            })}
          </div>
        </div>
      )}
      </div>
    </div>
  );
};

export default WorkflowsPage;
