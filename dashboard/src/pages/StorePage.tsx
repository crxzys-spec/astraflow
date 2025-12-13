import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useWorkflowPackages, useWorkflowPackagesStore } from "../store/workflowPackagesSlice";
import type { WorkflowPackageSummary } from "../client/models";
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
          className={`workflow-card__preview ${
            previewImage ? "" : "workflow-card__preview--empty"
          }`}
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

const StorePage = () => {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const canClone = useAuthStore((state) => state.hasRole(["admin", "workflow.editor"]));
  const canViewOwnPackages = useAuthStore((state) =>
    state.hasRole(["admin", "workflow.editor", "workflow.viewer"])
  );
  type StoreTab = "public" | "mine";
  const paramTab = searchParams.get("tab") === "mine" ? "mine" : "public";
  const [activeTab, setActiveTab] = useState<StoreTab>(paramTab);

  useEffect(() => {
    setActiveTab(paramTab);
  }, [paramTab]);

  useEffect(() => {
    if (activeTab === "mine" && !canViewOwnPackages) {
      setSearchParams({}, { replace: true });
    }
  }, [activeTab, canViewOwnPackages, setSearchParams]);

  const handleTabChange = (next: StoreTab) => {
    if (next === activeTab) {
      return;
    }
    setSearchParams(next === "public" ? {} : { tab: next }, { replace: true });
  };
  const [activeCloneId, setActiveCloneId] = useState<string | null>(null);
  const [cloneError, setCloneError] = useState<string | null>(null);
  const [deletePackageError, setDeletePackageError] = useState<string | null>(null);
  const [deletingPackageId, setDeletingPackageId] = useState<string | null>(null);

  const publicPackagesQuery = useWorkflowPackages(
    { visibility: "public" },
    { enabled: true },
  );
  const myPackagesQuery = useWorkflowPackages(
    { owner: "me" },
    { enabled: canViewOwnPackages },
  );

  const clonePackage = useWorkflowPackagesStore((state) => state.clonePackage);
  const deletePackage = useWorkflowPackagesStore((state) => state.deletePackage);

  const publicPackages = publicPackagesQuery.items ?? [];
  const publicErrorMessage = (publicPackagesQuery.error as { message?: string } | undefined)?.message ?? null;
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
    if (!window.confirm(`Delete package "${pkg.displayName}"? This hides it from the Store.`)) {
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
              const isDeleting =
                deletingPackageId === pkg.id;
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

  const heading = activeTab === "public" ? "Workflow Store" : "My Packages";
  const subheading =
    activeTab === "public"
      ? "Browse published workflows and clone them into your personal workspace."
      : "Review packages you have published to the store.";

  return (
    <div className="card stack store-panel">
      <header className="card__header">
        <div>
          <h2>{heading}</h2>
          <p className="text-subtle">{subheading}</p>
        </div>
      </header>
      <div className="store-tabs">
        <button
          type="button"
          className={`store-tab ${activeTab === "public" ? "store-tab--active" : ""}`}
          onClick={() => handleTabChange("public")}
        >
          Discover
        </button>
        <button
          type="button"
          className={`store-tab ${activeTab === "mine" ? "store-tab--active" : ""}`}
          onClick={() => handleTabChange("mine")}
          disabled={!canViewOwnPackages}
          title={!canViewOwnPackages ? "Requires workflow.viewer access." : undefined}
        >
          My Packages
        </button>
      </div>
      <div className="store-content">
        {activeTab === "public" ? renderPublicTab() : renderMyTab()}
      </div>
    </div>
  );
};

export default StorePage;
