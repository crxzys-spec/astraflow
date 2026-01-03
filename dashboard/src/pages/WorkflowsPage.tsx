import { useEffect, useMemo } from "react";
import type { CSSProperties } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuthStore } from "@store/authSlice";
import { useToolbarStore } from "../features/builder/hooks/useToolbar";
import { useWorkflows } from "../store/workflowsSlice";
import type { WorkflowModel } from "../services/workflows";
import { getHubBrowseUrl } from "../lib/hubLinks";

const WorkflowsPage = () => {
  const workflowsQuery = useWorkflows({ limit: 48 }, { enabled: true });
  const canCreateWorkflow = useAuthStore((state) => state.hasRole(["admin", "workflow.editor"]));
  const navigate = useNavigate();
  const hubBrowseUrl = getHubBrowseUrl("workflows");

  const workflows = workflowsQuery.items ?? [];
  const isLoading = workflowsQuery.isLoading;
  const isError = workflowsQuery.isError;
  const errorMessage =
    (workflowsQuery.error as { message?: string } | undefined)?.message ??
    (workflowsQuery.error as { response?: { data?: { message?: string } } } | undefined)?.response
      ?.data?.message;

  const setToolbar = useToolbarStore((state) => state.setContent);
  const workflowStats = useMemo(() => {
    const owners = new Set<string>();
    const tags = new Set<string>();
    workflows.forEach((workflow) => {
      const ownerDisplay = workflow.metadata?.ownerName ?? workflow.metadata?.ownerId;
      if (ownerDisplay) {
        owners.add(ownerDisplay);
      }
      const workflowTags = workflow.metadata?.tags ?? workflow.tags ?? [];
      workflowTags.forEach((tag) => tags.add(tag));
    });
    return {
      total: workflows.length,
      owners: owners.size,
      tags: tags.size,
    };
  }, [workflows]);

  const toolbarContent = useMemo(
    () => (
      <div className="toolbar-buttons">
        <Link className="btn btn--ghost" to="/hub/workflows">
          Hub Library
        </Link>
        {canCreateWorkflow && (
          <Link className="btn btn--ghost" to="/workflows/new">
            <span className="btn__icon" aria-hidden="true">
              <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6">
                <path d="M10 4v12" />
                <path d="M4 10h12" />
              </svg>
            </span>
            Create
          </Link>
        )}
      </div>
    ),
    [canCreateWorkflow],
  );

  useEffect(() => {
    setToolbar(toolbarContent);
    return () => setToolbar(null);
  }, [toolbarContent, setToolbar]);

  const handleOpen = (workflow: WorkflowModel) => {
    navigate(`/workflows/${workflow.id}`);
  };

  return (
    <div className="card stack package-center-panel workflows-panel">
      <div className="workflow-deck">
        <div className="workflow-deck__rail">
          <div className="workflow-deck__intro">
            <p className="workflow-deck__eyebrow">Workflow Library</p>
            <p className="workflow-deck__subtitle">
              Manage local workflows and open them in the interactive builder.
            </p>
          </div>
          <div className="workflow-deck__stats">
            <div className="workflow-deck__stat">
              <span className="workflow-deck__stat-label">Total</span>
              <strong>{isLoading ? "--" : workflowStats.total}</strong>
              <span className="workflow-deck__stat-sublabel">Local workflows</span>
            </div>
            <div className="workflow-deck__stat">
              <span className="workflow-deck__stat-label">Owners</span>
              <strong>{isLoading ? "--" : workflowStats.owners}</strong>
              <span className="workflow-deck__stat-sublabel">Maintainers</span>
            </div>
            <div className="workflow-deck__stat">
              <span className="workflow-deck__stat-label">Tags</span>
              <strong>{isLoading ? "--" : workflowStats.tags}</strong>
              <span className="workflow-deck__stat-sublabel">Categories</span>
            </div>
          </div>
        </div>
        <div className="package-center-content workflow-deck__content">
          {hubBrowseUrl && (
            <div className="card card--surface">
              <p className="text-subtle">
                Looking for shared workflows?{" "}
                <a href={hubBrowseUrl} target="_blank" rel="noreferrer">
                  Browse on Hub
                </a>
                .
              </p>
            </div>
          )}
          {isLoading && (
            <div className="card card--surface">
              <p>Loading local workflows...</p>
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
              <p>No local workflows found yet.</p>
            </div>
          )}

          {!isLoading && !isError && workflows.length > 0 && (
            <div className="workflow-grid-shell">
              <div className="workflow-grid">
                {workflows.map((workflow, index) => {
                  const tags = workflow.metadata?.tags ?? workflow.tags ?? [];
                  const visibleTags = tags.slice(0, 3);
                  const extraTagCount = Math.max(0, tags.length - visibleTags.length);
                  const description = workflow.metadata?.description ?? "No description yet.";
                  const ownerDisplay =
                    workflow.metadata?.ownerName ?? workflow.metadata?.ownerId ?? "Unassigned";
                  const previewImage = workflow.previewImage ?? null;
                  const workflowName = workflow.metadata?.name ?? workflow.id;
                  const namespaceLabel = workflow.metadata?.namespace ?? "default";
                  const idShort =
                    workflow.id.length > 12
                      ? `${workflow.id.slice(0, 8)}...${workflow.id.slice(-4)}`
                      : workflow.id;
                  const cardStyle = { "--stagger": index } as CSSProperties;
                  return (
                    <article
                      key={workflow.id}
                      className="card card--surface workflow-card workflow-card--accent"
                      style={cardStyle}
                    >
                      <div className="workflow-card__media">
                        <div
                          className={`workflow-card__preview ${
                            previewImage ? "" : "workflow-card__preview--empty"
                          }`}
                        >
                          {previewImage ? (
                            <img
                              src={previewImage}
                              alt={`${workflowName} preview`}
                              loading="lazy"
                            />
                          ) : (
                            <div className="workflow-card__preview-placeholder">
                              <div className="workflow-card__placeholder-icon" aria-hidden="true">
                                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
                                  <rect x="3" y="4" width="18" height="14" rx="2" />
                                  <path d="M7 9h10" />
                                  <path d="M7 13h6" />
                                </svg>
                              </div>
                              <div className="workflow-card__placeholder-copy">
                                <span className="workflow-card__placeholder-title">Snapshot pending</span>
                                <span className="workflow-card__placeholder-subtitle">
                                  Run the workflow to capture a preview.
                                </span>
                              </div>
                            </div>
                          )}
                        </div>
                        <header className="workflow-card__header">
                          <div className="workflow-card__identity">
                            <small className="workflow-card__eyebrow">Local workflow</small>
                            <h3>{workflowName}</h3>
                            <p className="workflow-card__owner">@{ownerDisplay}</p>
                          </div>
                          <div className="workflow-card__chips workflow-card__chips--header">
                            <span className="chip workflow-pill">{namespaceLabel}</span>
                            <span className="chip workflow-pill">Local</span>
                          </div>
                        </header>
                      </div>
                      <div className="workflow-card__body">
                        <p className="workflow-card__description">{description}</p>
                        {tags.length > 0 ? (
                          <div className="workflow-card__tags">
                            {visibleTags.map((tag) => (
                              <span key={tag} className="workflow-tag">
                                {tag}
                              </span>
                            ))}
                            {extraTagCount > 0 && (
                              <span className="workflow-tag workflow-tag--ghost">
                                +{extraTagCount} more
                              </span>
                            )}
                          </div>
                        ) : (
                          <div className="workflow-card__tags workflow-card__tags--empty">
                            No tags yet
                          </div>
                        )}
                        <div className="workflow-card__actions-row">
                          <div className="workflow-card__action-buttons">
                            <button
                              className="btn workflow-btn workflow-btn--ghost"
                              type="button"
                              onClick={() => handleOpen(workflow)}
                            >
                              Open Builder
                            </button>
                          </div>
                          <div className="workflow-card__signature" title={workflow.id}>
                            <span>ID</span>
                            <code>{idShort}</code>
                          </div>
                        </div>
                      </div>
                    </article>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default WorkflowsPage;
