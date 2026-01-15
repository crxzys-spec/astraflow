import { useEffect, useMemo, useState } from "react";
import type { CSSProperties } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuthStore } from "@store/authSlice";
import { useToolbarStore } from "../features/builder/hooks/useToolbar";
import { useWorkflows, useWorkflowsStore } from "../store/workflowsSlice";
import type { WorkflowModel } from "../services/workflows";
import { getHubBrowseUrl } from "../lib/hubLinks";
import { useMessageCenter } from "../components/MessageCenter";
import { resolveApiErrorMessage } from "../lib/apiErrors";
import { resolveLocalizedText } from "../lib/manifestText";
import { useTranslation } from "react-i18next";

const getErrorMessage = (error: unknown, fallback: string): string =>
  resolveApiErrorMessage(error, fallback);

const WorkflowsPage = () => {
  const { t, i18n } = useTranslation();
  const workflowsQuery = useWorkflows({ limit: 48 }, { enabled: true });
  const canCreateWorkflow = useAuthStore((state) => state.hasRole(["admin", "workflow.editor"]));
  const navigate = useNavigate();
  const hubBrowseUrl = getHubBrowseUrl("workflows");
  const { pushMessage } = useMessageCenter();
  const deleteWorkflow = useWorkflowsStore((state) => state.deleteWorkflow);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [activeDeleteId, setActiveDeleteId] = useState<string | null>(null);

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
          {t("nav.hubLibrary")}
        </Link>
        {canCreateWorkflow && (
          <Link className="btn btn--ghost" to="/workflows/new">
            <span className="btn__icon" aria-hidden="true">
              <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6">
                <path d="M10 4v12" />
                <path d="M4 10h12" />
              </svg>
            </span>
            {t("common.create")}
          </Link>
        )}
      </div>
    ),
    [canCreateWorkflow, i18n.language, t],
  );

  useEffect(() => {
    setToolbar(toolbarContent);
    return () => setToolbar(null);
  }, [toolbarContent, setToolbar]);

  const handleOpen = (workflow: WorkflowModel) => {
    navigate(`/workflows/${workflow.id}`);
  };

  const handleDelete = async (workflow: WorkflowModel) => {
    if (!canCreateWorkflow) {
      setDeleteError(t("workflows.deletePermission"));
      return;
    }
    const workflowName = resolveLocalizedText(workflow.metadata?.name) ?? workflow.id;
    if (!window.confirm(t("workflows.deleteConfirm", { name: workflowName }))) {
      return;
    }
    setActiveDeleteId(workflow.id);
    setDeleteError(null);
    try {
      await deleteWorkflow(workflow.id);
      pushMessage({
        tone: "success",
        content: t("workflows.deleteSuccess", { name: workflowName }),
      });
    } catch (error) {
      setDeleteError(getErrorMessage(error, t("workflows.deleteFailed")));
    } finally {
      setActiveDeleteId(null);
    }
  };

  return (
    <>
      <div className="card stack package-center-panel workflows-panel">
        <div className="workflow-deck">
          <div className="workflow-deck__rail">
            <div className="workflow-deck__intro">
              <p className="workflow-deck__eyebrow">{t("workflows.libraryTitle")}</p>
              <p className="workflow-deck__subtitle">{t("workflows.librarySubtitle")}</p>
            </div>
            <div className="workflow-deck__stats">
              <div className="workflow-deck__stat">
                <span className="workflow-deck__stat-label">{t("workflows.stats.totalLabel")}</span>
                <strong>{isLoading ? "--" : workflowStats.total}</strong>
                <span className="workflow-deck__stat-sublabel">{t("workflows.stats.totalSublabel")}</span>
              </div>
              <div className="workflow-deck__stat">
                <span className="workflow-deck__stat-label">{t("workflows.stats.ownersLabel")}</span>
                <strong>{isLoading ? "--" : workflowStats.owners}</strong>
                <span className="workflow-deck__stat-sublabel">{t("workflows.stats.ownersSublabel")}</span>
              </div>
              <div className="workflow-deck__stat">
                <span className="workflow-deck__stat-label">{t("workflows.stats.tagsLabel")}</span>
                <strong>{isLoading ? "--" : workflowStats.tags}</strong>
                <span className="workflow-deck__stat-sublabel">{t("workflows.stats.tagsSublabel")}</span>
              </div>
            </div>
          </div>
          <div className="package-center-content workflow-deck__content">
            {deleteError && (
              <div className="card card--error">
                <p className="error">{deleteError}</p>
                <button className="btn" type="button" onClick={() => setDeleteError(null)}>
                  {t("common.dismiss")}
                </button>
              </div>
            )}
            {hubBrowseUrl && (
              <div className="card card--surface">
                <p className="text-subtle">
                  {t("workflows.hubHint")}{" "}
                  <a href={hubBrowseUrl} target="_blank" rel="noreferrer">
                    {t("workflows.browseHub")}
                  </a>
                  .
                </p>
              </div>
            )}
            {isLoading && (
              <div className="card card--surface">
                <p>{t("workflows.loading")}</p>
              </div>
            )}

            {isError && (
              <div className="card card--error">
                <p className="error">
                  {t("workflows.loadFailed", {
                    message: errorMessage ?? t("common.unknownError"),
                  })}
                </p>
                <button className="btn" type="button" onClick={() => workflowsQuery.refetch()}>
                  {t("common.retry")}
                </button>
              </div>
            )}

            {!isLoading && !isError && workflows.length === 0 && (
              <div className="card card--surface">
                <p>{t("workflows.empty")}</p>
              </div>
            )}

            {!isLoading && !isError && workflows.length > 0 && (
              <div className="workflow-grid-shell">
                <div className="workflow-grid">
                  {workflows.map((workflow, index) => {
                    const tags = workflow.metadata?.tags ?? workflow.tags ?? [];
                    const visibleTags = tags.slice(0, 3);
                    const extraTagCount = Math.max(0, tags.length - visibleTags.length);
                    const description =
                      resolveLocalizedText(workflow.metadata?.description) ?? t("workflows.noDescription");
                    const ownerDisplay =
                      workflow.metadata?.ownerName ?? workflow.metadata?.ownerId ?? t("common.unassigned");
                    const previewImage = workflow.previewImage ?? null;
                    const workflowName = resolveLocalizedText(workflow.metadata?.name) ?? workflow.id;
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
                                  <span className="workflow-card__placeholder-title">
                                    {t("workflows.snapshotPending")}
                                  </span>
                                  <span className="workflow-card__placeholder-subtitle">
                                    {t("workflows.snapshotHint")}
                                  </span>
                                </div>
                              </div>
                            )}
                          </div>
                          <header className="workflow-card__header">
                            <div className="workflow-card__identity">
                              <small className="workflow-card__eyebrow">{t("workflows.localWorkflow")}</small>
                              <h3>{workflowName}</h3>
                              <p className="workflow-card__owner">@{ownerDisplay}</p>
                            </div>
                            <div className="workflow-card__chips workflow-card__chips--header">
                              <span className="chip workflow-pill">{namespaceLabel}</span>
                              <span className="chip workflow-pill">{t("common.local")}</span>
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
                                  {t("workflows.moreTags", { count: extraTagCount })}
                                </span>
                              )}
                            </div>
                          ) : (
                            <div className="workflow-card__tags workflow-card__tags--empty">
                              {t("workflows.noTags")}
                            </div>
                          )}
                          <div className="workflow-card__actions-row">
                            <div className="workflow-card__action-buttons">
                              <button
                                className="btn workflow-btn workflow-btn--ghost"
                                type="button"
                                onClick={() => handleOpen(workflow)}
                              >
                                {t("workflows.openBuilder")}
                              </button>
                              {canCreateWorkflow && (
                                <button
                                  className="btn workflow-btn workflow-btn--ghost workflow-btn--danger"
                                  type="button"
                                  onClick={() => handleDelete(workflow)}
                                  disabled={activeDeleteId === workflow.id}
                                >
                                  {activeDeleteId === workflow.id
                                    ? t("workflows.deleting")
                                    : t("workflows.delete")}
                                </button>
                              )}
                            </div>
                            <div className="workflow-card__signature" title={workflow.id}>
                              <span>{t("common.id")}</span>
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
    </>
  );
};

export default WorkflowsPage;
