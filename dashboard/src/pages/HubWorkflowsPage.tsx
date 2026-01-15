import { useEffect, useMemo, useState } from "react";
import type { CSSProperties } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuthStore } from "@store/authSlice";
import { useToolbarStore } from "../features/builder/hooks/useToolbar";
import { useHubWorkflows } from "../store/hubWorkflowsSlice";
import type { HubWorkflowSummaryModel } from "../services/hubWorkflows";
import { importHubWorkflow } from "../services/hubWorkflows";
import { getHubBrowseUrl, getHubItemUrl } from "../lib/hubLinks";
import { useTranslation } from "react-i18next";

const HubWorkflowsPage = () => {
  const { t, i18n } = useTranslation();
  const workflowsQuery = useHubWorkflows(undefined, { enabled: true });
  const canImportWorkflow = useAuthStore((state) => state.hasRole(["admin", "workflow.editor"]));
  const [importError, setImportError] = useState<string | null>(null);
  const [importingWorkflowId, setImportingWorkflowId] = useState<string | null>(null);
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
      const ownerDisplay = workflow.ownerName ?? workflow.ownerId;
      if (ownerDisplay) {
        owners.add(ownerDisplay);
      }
      const workflowTags = workflow.tags ?? [];
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
        <Link className="btn btn--ghost" to="/workflows">
          {t("nav.localWorkflows")}
        </Link>
        {hubBrowseUrl && (
          <a className="btn btn--ghost" href={hubBrowseUrl} target="_blank" rel="noreferrer">
            {t("common.openHub")}
          </a>
        )}
      </div>
    ),
    [hubBrowseUrl, i18n.language, t],
  );

  useEffect(() => {
    setToolbar(toolbarContent);
    return () => setToolbar(null);
  }, [toolbarContent, setToolbar]);

  const handleImport = async (workflow: HubWorkflowSummaryModel) => {
    if (!canImportWorkflow) {
      setImportError(t("hubWorkflows.importPermission"));
      return;
    }
    setImportError(null);
    setImportingWorkflowId(workflow.id);
    try {
      const payload = workflow.latestVersion ? { version: workflow.latestVersion } : undefined;
      const response = await importHubWorkflow(workflow.id, payload);
      if (response?.workflowId) {
        navigate(`/workflows/${response.workflowId}`);
      }
    } catch (error) {
      const defaultMessage = t("hubWorkflows.importFailed");
      const responseMessage =
        (error as { response?: { data?: { message?: string } } })?.response?.data?.message;
      setImportError(responseMessage ?? (error as Error | undefined)?.message ?? defaultMessage);
    } finally {
      setImportingWorkflowId(null);
    }
  };

  return (
    <div className="card stack package-center-panel workflows-panel">
      <div className="workflow-deck">
        <div className="workflow-deck__rail">
          <div className="workflow-deck__intro">
            <p className="workflow-deck__eyebrow">{t("hubWorkflows.libraryTitle")}</p>
            <p className="workflow-deck__subtitle">{t("hubWorkflows.librarySubtitle")}</p>
          </div>
          <div className="workflow-deck__stats">
            <div className="workflow-deck__stat">
              <span className="workflow-deck__stat-label">{t("hubWorkflows.stats.totalLabel")}</span>
              <strong>{isLoading ? "--" : workflowStats.total}</strong>
              <span className="workflow-deck__stat-sublabel">{t("hubWorkflows.stats.totalSublabel")}</span>
            </div>
            <div className="workflow-deck__stat">
              <span className="workflow-deck__stat-label">{t("hubWorkflows.stats.ownersLabel")}</span>
              <strong>{isLoading ? "--" : workflowStats.owners}</strong>
              <span className="workflow-deck__stat-sublabel">{t("hubWorkflows.stats.ownersSublabel")}</span>
            </div>
            <div className="workflow-deck__stat">
              <span className="workflow-deck__stat-label">{t("hubWorkflows.stats.tagsLabel")}</span>
              <strong>{isLoading ? "--" : workflowStats.tags}</strong>
              <span className="workflow-deck__stat-sublabel">{t("hubWorkflows.stats.tagsSublabel")}</span>
            </div>
          </div>
        </div>
        <div className="package-center-content workflow-deck__content">
          {importError && (
            <div className="card card--error">
              <p className="error">
                {t("hubWorkflows.importError", { message: importError })}
              </p>
            </div>
          )}
          {isLoading && (
            <div className="card card--surface">
              <p>{t("hubWorkflows.loading")}</p>
            </div>
          )}

          {isError && (
            <div className="card card--error">
              <p className="error">
                {t("hubWorkflows.loadFailed", {
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
              <p>{t("hubWorkflows.empty")}</p>
            </div>
          )}

          {!isLoading && !isError && workflows.length > 0 && (
            <div className="workflow-grid-shell">
              <div className="workflow-grid">
                {workflows.map((workflow, index) => {
                  const tags = workflow.tags ?? [];
                  const visibleTags = tags.slice(0, 3);
                  const extraTagCount = Math.max(0, tags.length - visibleTags.length);
                  const description = workflow.summary ?? workflow.description ?? t("hubWorkflows.noDescription");
                  const ownerDisplay = workflow.ownerName ?? workflow.ownerId ?? t("common.unassigned");
                  const workflowName = workflow.name ?? workflow.id;
                  const versionLabel = workflow.latestVersion ?? "latest";
                  const visibilityValue = workflow.visibility ?? "public";
                  const idShort =
                    workflow.id.length > 12
                      ? `${workflow.id.slice(0, 8)}...${workflow.id.slice(-4)}`
                      : workflow.id;
                  const cardStyle = { "--stagger": index } as CSSProperties;
                  const hubItemUrl = getHubItemUrl("workflows", workflow.id) ?? hubBrowseUrl;
                  return (
                    <article
                      key={workflow.id}
                      className="card card--surface workflow-card workflow-card--accent"
                      style={cardStyle}
                    >
                      <div className="workflow-card__media">
                          <div className="workflow-card__preview workflow-card__preview--empty">
                            <div className="workflow-card__preview-placeholder">
                              <div className="workflow-card__placeholder-icon" aria-hidden="true">
                                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
                                  <rect x="3" y="4" width="18" height="14" rx="2" />
                                  <path d="M7 9h10" />
                                  <path d="M7 13h6" />
                                </svg>
                              </div>
                              <div className="workflow-card__placeholder-copy">
                                <span className="workflow-card__placeholder-title">{t("hubWorkflows.previewTitle")}</span>
                                <span className="workflow-card__placeholder-subtitle">
                                  {t("hubWorkflows.previewSubtitle")}
                                </span>
                              </div>
                            </div>
                          </div>
                          <header className="workflow-card__header">
                            <div className="workflow-card__identity">
                              <small className="workflow-card__eyebrow">{t("hubWorkflows.hubWorkflow")}</small>
                              <h3>{workflowName}</h3>
                              <p className="workflow-card__owner">@{ownerDisplay}</p>
                            </div>
                            <div className="workflow-card__chips workflow-card__chips--header">
                            <span className="chip workflow-pill">v{versionLabel}</span>
                            <span className="chip workflow-pill">
                              {visibilityValue.charAt(0).toUpperCase() + visibilityValue.slice(1)}
                            </span>
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
                              disabled={!canImportWorkflow || importingWorkflowId === workflow.id}
                              onClick={() => handleImport(workflow)}
                            >
                              {importingWorkflowId === workflow.id
                                ? t("hubWorkflows.importing")
                                : t("hubWorkflows.import")}
                            </button>
                            {hubItemUrl && (
                              <a
                                className="btn workflow-btn workflow-btn--ghost"
                                href={hubItemUrl}
                                target="_blank"
                                rel="noreferrer"
                              >
                                {t("hubWorkflows.viewInHub")}
                              </a>
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
  );
};

export default HubWorkflowsPage;
