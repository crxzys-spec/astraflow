import { useEffect, useState, type ReactNode } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useWorkflowPackages, useWorkflowPackagesStore } from "../../../store/workflowPackagesSlice";
import type { WorkflowPackageSummary } from "../../../client/models";
import { useAuthStore } from "@store/authSlice";

const getErrorMessage = (error: unknown, fallback: string): string => {
  if (error && typeof error === "object" && "response" in error) {
    const response = (error as { response?: { data?: { message?: string } } }).response;
    if (response?.data?.message) {
      return response.data.message;
    }
  }
  if (error instanceof Error) {
    return error.message;
  }
  return fallback;
};

const ArrowUpRightIcon = () => (
  <svg
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
    width="16"
    height="16"
    aria-hidden
    focusable="false"
  >
    <path d="M7 17 17 7" />
    <path d="M7 7h10v10" />
  </svg>
);

const PackageCard = ({
  pkg,
  actionSlot,
}: {
  pkg: WorkflowPackageSummary;
  actionSlot?: ReactNode;
}) => {
  const latestVersion = pkg.latestVersion;
  const previewImage = pkg.previewImage ?? pkg.latestVersion?.previewImage ?? null;
  const visibilityLabel = pkg.visibility.charAt(0).toUpperCase() + pkg.visibility.slice(1);
  const ownerDisplay = pkg.ownerName ?? pkg.ownerId ?? "Unassigned";
  const latestVersionLabel = latestVersion?.version ?? "?";
  const description = pkg.summary ?? "No description provided.";
  return (
    <article className="card card--surface workflow-card workflow-card--accent">
      <div className="workflow-card__media">
        <div
          className={`workflow-card__preview ${previewImage ? "" : "workflow-card__preview--empty"}`}
        >
          {previewImage ? (
            <img src={previewImage} alt={`${pkg.displayName} preview`} loading="lazy" />
          ) : (
            <div className="workflow-card__preview-placeholder">Snapshot pending</div>
          )}
        </div>
        <header className="workflow-card__header">
          <div className="workflow-card__identity">
            <small className="workflow-card__eyebrow">Package</small>
            <h3>{pkg.displayName}</h3>
            <p className="workflow-card__owner">@{ownerDisplay}</p>
          </div>
          <div className="workflow-card__chips workflow-card__chips--header">
            <span className="chip chip--self">self</span>
            <span className="chip chip--ghost">v{latestVersionLabel}</span>
            <span className="chip chip--ghost">{visibilityLabel}</span>
          </div>
        </header>
      </div>
      <div className="workflow-card__body">
        <p className="workflow-card__description">{description}</p>
        {actionSlot && (
          <div className="workflow-card__actions-row">
            <div className="workflow-card__action-buttons">{actionSlot}</div>
          </div>
        )}
        <footer className="workflow-card__footer">
          <div className="workflow-card__signature">
            <span>Package ID</span>
            <code>{pkg.id}</code>
          </div>
        </footer>
      </div>
    </article>
  );
};

const PackageCenterPage = () => {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const canClone = useAuthStore((state) => state.hasRole(["admin", "workflow.editor"]));
  const canViewOwnPackages = useAuthStore((state) =>
    state.hasRole(["admin", "workflow.editor", "workflow.viewer"])
  );
  type PackageCenterTab = "public" | "mine";
  const paramTab = searchParams.get("tab") === "mine" ? "mine" : "public";
  const [activeTab, setActiveTab] = useState<PackageCenterTab>(paramTab);

  useEffect(() => {
    setActiveTab(paramTab);
  }, [paramTab]);

  useEffect(() => {
    if (activeTab === "mine" && !canViewOwnPackages) {
      setSearchParams({}, { replace: true });
    }
  }, [activeTab, canViewOwnPackages, setSearchParams]);

  const handleTabChange = (next: PackageCenterTab) => {
    if (next === activeTab) {
      return;
    }
    setSearchParams(next === "public" ? {} : { tab: next }, { replace: true });
  };
  const [activeCloneId, setActiveCloneId] = useState<string | null>(null);
  const [cloneError, setCloneError] = useState<string | null>(null);
  const [deletePackageError, setDeletePackageError] = useState<string | null>(null);
  const [deletingPackageId, setDeletingPackageId] = useState<string | null>(null);

  const publicPackagesQuery = useWorkflowPackages({ visibility: "public" }, { enabled: true });
  const myPackagesQuery = useWorkflowPackages({ owner: "me" }, { enabled: canViewOwnPackages });

  const clonePackage = useWorkflowPackagesStore((state) => state.clonePackage);
  const deletePackage = useWorkflowPackagesStore((state) => state.deletePackage);

  const publicPackages = publicPackagesQuery.items ?? [];
  const publicErrorMessage =
    (publicPackagesQuery.error as { message?: string } | undefined)?.message ?? null;
  const myPackages = myPackagesQuery.items ?? [];
  const myErrorMessage = (myPackagesQuery.error as { message?: string } | undefined)?.message ?? null;

  const handleClone = (pkg: WorkflowPackageSummary) => {
    if (!canClone) {
      setCloneError("You need workflow.editor access to clone packages.");
      return;
    }
    const payload = pkg.latestVersion?.id
      ? { versionId: pkg.latestVersion.id, workflowName: pkg.displayName }
      : { workflowName: pkg.displayName };
    setActiveCloneId(pkg.id);
    setCloneError(null);
    clonePackage(pkg.id, payload)
      .then((response) => {
        const workflowId = response?.workflowId;
        if (workflowId) {
          navigate(`/workflows/${workflowId}`);
        }
      })
      .catch((error) => {
        setCloneError(getErrorMessage(error, "Failed to clone workflow."));
      })
      .finally(() => {
        setActiveCloneId(null);
      });
  };

  const handleDeletePackage = async (pkg: WorkflowPackageSummary) => {
    if (!window.confirm(`Delete package "${pkg.displayName}"? This hides it from the Package Center.`)) {
      return;
    }
    setDeletePackageError(null);
    setDeletingPackageId(pkg.id);
    try {
      await deletePackage(pkg.id);
      await Promise.all([myPackagesQuery.refetch(), publicPackagesQuery.refetch()]);
    } catch (error) {
      setDeletePackageError(getErrorMessage(error, "Failed to delete package."));
    } finally {
      setDeletingPackageId(null);
    }
  };

  const renderPublicTab = () => (
    <>
      {cloneError && (
        <div className="card card--error">
          <p className="error">{cloneError}</p>
          <button className="btn" type="button" onClick={() => setCloneError(null)}>
            Dismiss
          </button>
        </div>
      )}

      {publicPackagesQuery.isLoading && (
        <div className="card card--surface">
          <p>Loading published workflows...</p>
        </div>
      )}
      {publicPackagesQuery.isError && (
        <div className="card card--error">
          <p className="error">
            Unable to load published workflows: {publicErrorMessage ?? "Unknown error"}
          </p>
          <button className="btn" type="button" onClick={() => publicPackagesQuery.refetch()}>
            Retry
          </button>
        </div>
      )}
      {!publicPackagesQuery.isLoading &&
        !publicPackagesQuery.isError &&
        publicPackages.length === 0 && (
          <div className="card card--surface">
            <p>No published workflows available yet.</p>
          </div>
        )}
      {!publicPackagesQuery.isLoading &&
        !publicPackagesQuery.isError &&
        publicPackages.length > 0 && (
          <div className="workflow-grid-shell">
            <div className="workflow-grid">
              {publicPackages.map((pkg) => (
                <PackageCard
                  key={pkg.id}
                  pkg={pkg}
                  actionSlot={
                    <button
                      className="btn btn--primary"
                      type="button"
                      onClick={() => handleClone(pkg)}
                      disabled={!canClone || activeCloneId === pkg.id}
                    >
                      {activeCloneId === pkg.id ? "Cloning..." : "Clone"}
                    </button>
                  }
                />
              ))}
            </div>
          </div>
        )}
    </>
  );

  const renderMyTab = () => {
    if (!canViewOwnPackages) {
      return (
        <div className="card card--surface">
          <p>You need workflow.viewer or workflow.editor access to view your published packages.</p>
        </div>
      );
    }
    if (myPackagesQuery.isLoading) {
      return (
        <div className="card card--surface">
          <p>Loading your packages...</p>
        </div>
      );
    }
    if (myPackagesQuery.isError) {
      return (
        <div className="card card--error">
          <p className="error">Unable to load packages: {myErrorMessage ?? "Unknown error"}</p>
          <button className="btn" type="button" onClick={() => myPackagesQuery.refetch()}>
            Retry
          </button>
        </div>
      );
    }
    if (myPackages.length === 0) {
      return (
        <div className="card card--surface">
          <p>You have not published any packages yet.</p>
        </div>
      );
    }
    return (
      <>
        {deletePackageError && (
          <div className="card card--error">
            <p className="error">Unable to delete package: {deletePackageError}</p>
            <button className="btn" type="button" onClick={() => setDeletePackageError(null)}>
              Dismiss
            </button>
          </div>
        )}
        <div className="workflow-grid-shell">
          <div className="workflow-grid">
            {myPackages.map((pkg) => {
              const isDeleting = deletingPackageId === pkg.id;
              return (
                <PackageCard
                  key={pkg.id}
                  pkg={pkg}
                  actionSlot={
                    <button
                      className="btn btn--ghost"
                      type="button"
                      onClick={() => handleDeletePackage(pkg)}
                      disabled={Boolean(deletingPackageId)}
                    >
                      {isDeleting ? "Deleting..." : "Delete"}
                    </button>
                  }
                />
              );
            })}
          </div>
        </div>
      </>
    );
  };

  const heading = activeTab === "public" ? "Package Center" : "My Packages";
  const subheading =
    activeTab === "public"
      ? "Discover published workflows and clone them into your workspace."
      : "Review packages you have published to the Package Center.";

  const publicCount = publicPackages?.length ?? 0;
  const myCount = myPackages?.length ?? 0;

  return (
    <div className="card stack package-center-panel">
      <header className="package-center-hero">
        <div className="package-center-hero__text">
          <p className="package-center-hero__eyebrow">Packages</p>
          <h2>{heading}</h2>
          <p className="text-subtle">{subheading}</p>
          <div className="package-center-stats">
            <span className="package-center-stat">
              Public<span className="package-center-stat__value">{publicCount}</span>
            </span>
            <span className="package-center-stat">
              My packages
              <span className="package-center-stat__value">
                {canViewOwnPackages ? myCount : "Locked"}
              </span>
            </span>
          </div>
        </div>
        <div className="package-center-hero__actions">
          <button
            type="button"
            className="btn btn--ghost"
            onClick={() => navigate("/workflows/new")}
            title="Create a workflow to publish"
          >
            Create Workflow
            <ArrowUpRightIcon />
          </button>
        </div>
      </header>
      <div className="package-center-tabs">
        <button
          type="button"
          className={`package-center-tab ${activeTab === "public" ? "package-center-tab--active" : ""}`}
          onClick={() => handleTabChange("public")}
        >
          Discover
        </button>
        <button
          type="button"
          className={`package-center-tab ${activeTab === "mine" ? "package-center-tab--active" : ""}`}
          onClick={() => handleTabChange("mine")}
          disabled={!canViewOwnPackages}
          title={!canViewOwnPackages ? "Requires workflow.viewer access." : undefined}
        >
          My Packages
        </button>
      </div>
      <div className="package-center-content">{activeTab === "public" ? renderPublicTab() : renderMyTab()}</div>
    </div>
  );
};

export default PackageCenterPage;
