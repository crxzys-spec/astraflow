import { useCallback, useEffect, useState, type ReactNode } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useHubPackages } from "../../../store/hubPackagesSlice";
import type { HubPackageSummaryModel } from "../../../services/hubPackages";
import { installHubPackage } from "../../../services/hubPackages";
import { listPackages } from "../../../services/packages";
import type { PackageSummary } from "../../../client/models";
import { useAuthStore } from "@store/authSlice";
import { useMessageCenter } from "../../../components/MessageCenter";
import { getHubBrowseUrl, getHubItemUrl } from "../../../lib/hubLinks";

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
  pkg: HubPackageSummaryModel;
  actionSlot?: ReactNode;
}) => {
  const visibilityValue = pkg.visibility ?? "public";
  const visibilityLabel = visibilityValue.charAt(0).toUpperCase() + visibilityValue.slice(1);
  const ownerDisplay = pkg.ownerName ?? pkg.ownerId ?? "Unassigned";
  const latestVersionLabel = pkg.latestVersion ?? "latest";
  const packageName = pkg.name;
  const description = pkg.description ?? "No description provided.";
  return (
    <article className="card card--surface workflow-card workflow-card--accent">
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
              <span className="workflow-card__placeholder-title">Preview on Hub</span>
              <span className="workflow-card__placeholder-subtitle">
                Readme and versions are available on Hub.
              </span>
            </div>
          </div>
        </div>
        <header className="workflow-card__header">
          <div className="workflow-card__identity">
            <small className="workflow-card__eyebrow">Package</small>
            <h3>{packageName}</h3>
            <p className="workflow-card__owner">@{ownerDisplay}</p>
          </div>
          <div className="workflow-card__chips workflow-card__chips--header">
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
            <span>Package</span>
            <code>{pkg.name}</code>
          </div>
        </footer>
      </div>
    </article>
  );
};

const LocalPackageCard = ({ pkg }: { pkg: PackageSummary }) => {
  const visibilityValue = pkg.visibility ?? "internal";
  const visibilityLabel = visibilityValue.charAt(0).toUpperCase() + visibilityValue.slice(1);
  const ownerDisplay = pkg.ownerId ?? "Local";
  const latestVersionLabel = pkg.latestVersion ?? pkg.defaultVersion ?? pkg.versions?.[0] ?? "local";
  const packageName = pkg.name;
  const description = pkg.description ?? "Installed in this workspace.";
  return (
    <article className="card card--surface workflow-card workflow-card--accent">
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
              <span className="workflow-card__placeholder-title">Installed locally</span>
              <span className="workflow-card__placeholder-subtitle">
                Available to all workflows in this workspace.
              </span>
            </div>
          </div>
        </div>
        <header className="workflow-card__header">
          <div className="workflow-card__identity">
            <small className="workflow-card__eyebrow">Local package</small>
            <h3>{packageName}</h3>
            <p className="workflow-card__owner">@{ownerDisplay}</p>
          </div>
          <div className="workflow-card__chips workflow-card__chips--header">
            <span className="chip chip--ghost">v{latestVersionLabel}</span>
            <span className="chip chip--ghost">{visibilityLabel}</span>
          </div>
        </header>
      </div>
      <div className="workflow-card__body">
        <p className="workflow-card__description">{description}</p>
        <footer className="workflow-card__footer">
          <div className="workflow-card__signature">
            <span>Package</span>
            <code>{pkg.name}</code>
          </div>
        </footer>
      </div>
    </article>
  );
};

const PackageCenterPage = () => {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const canInstall = useAuthStore((state) => state.hasRole(["admin", "workflow.editor"]));
  const canViewOwnPackages = useAuthStore((state) =>
    state.hasRole(["admin", "workflow.editor", "workflow.viewer"])
  );
  const canViewLocalPackages = useAuthStore((state) =>
    state.hasRole(["admin", "workflow.editor", "workflow.viewer"])
  );
  const user = useAuthStore((state) => state.user);
  const { pushMessage } = useMessageCenter();
  const hubBrowseUrl = getHubBrowseUrl("packages");
  type PackageCenterTab = "public" | "mine" | "local";
  const rawTab = searchParams.get("tab");
  const paramTab: PackageCenterTab =
    rawTab === "mine" || rawTab === "local" ? rawTab : "public";
  const [activeTab, setActiveTab] = useState<PackageCenterTab>(paramTab);

  useEffect(() => {
    setActiveTab(paramTab);
  }, [paramTab]);

  useEffect(() => {
    if (activeTab === "mine" && !canViewOwnPackages) {
      setSearchParams({}, { replace: true });
    }
    if (activeTab === "local" && !canViewLocalPackages) {
      setSearchParams({}, { replace: true });
    }
  }, [activeTab, canViewLocalPackages, canViewOwnPackages, setSearchParams]);

  const handleTabChange = (next: PackageCenterTab) => {
    if (next === activeTab) {
      return;
    }
    setSearchParams(next === "public" ? {} : { tab: next }, { replace: true });
  };
  const [activeInstallName, setActiveInstallName] = useState<string | null>(null);
  const [installError, setInstallError] = useState<string | null>(null);
  const [localPackages, setLocalPackages] = useState<PackageSummary[]>([]);
  const [localLoading, setLocalLoading] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);

  const ownerFilter = user?.userId ?? null;
  const publicPackagesQuery = useHubPackages({ pageSize: 48 }, { enabled: true });
  const myPackagesQuery = useHubPackages(
    { owner: ownerFilter ?? undefined, pageSize: 48 },
    { enabled: canViewOwnPackages && Boolean(ownerFilter) },
  );

  const publicPackages = publicPackagesQuery.items ?? [];
  const publicErrorMessage =
    (publicPackagesQuery.error as { message?: string } | undefined)?.message ?? null;
  const myPackages = myPackagesQuery.items ?? [];
  const myErrorMessage = (myPackagesQuery.error as { message?: string } | undefined)?.message ?? null;

  const handleInstall = (pkg: HubPackageSummaryModel) => {
    if (!canInstall) {
      setInstallError("You need workflow.editor access to install packages.");
      return;
    }
    const payload = pkg.latestVersion ? { version: pkg.latestVersion } : undefined;
    setActiveInstallName(pkg.name);
    setInstallError(null);
    installHubPackage(pkg.name, payload)
      .then((response) => {
        pushMessage({
          tone: "success",
          content: `Installed ${response.name}@${response.version}.`,
        });
      })
      .catch((error) => {
        setInstallError(getErrorMessage(error, "Failed to install package."));
      })
      .finally(() => {
        setActiveInstallName(null);
      });
  };

  const loadLocalPackages = useCallback(async () => {
    setLocalLoading(true);
    setLocalError(null);
    try {
      const items = await listPackages();
      setLocalPackages(items);
    } catch (error) {
      setLocalError(getErrorMessage(error, "Failed to load local packages."));
    } finally {
      setLocalLoading(false);
    }
  }, []);

  useEffect(() => {
    if (activeTab === "local" && canViewLocalPackages) {
      void loadLocalPackages();
    }
  }, [activeTab, canViewLocalPackages, loadLocalPackages]);

  const renderActions = (pkg: HubPackageSummaryModel, variant: "primary" | "ghost") => {
    const hubItemUrl = getHubItemUrl("packages", pkg.name) ?? hubBrowseUrl;
    return (
      <>
        <button
          className={`btn ${variant === "primary" ? "btn--primary" : "btn--ghost"}`}
          type="button"
          onClick={() => handleInstall(pkg)}
          disabled={!canInstall || activeInstallName === pkg.name}
        >
          {activeInstallName === pkg.name ? "Installing..." : "Install"}
        </button>
        {hubItemUrl && (
          <a className="btn btn--ghost" href={hubItemUrl} target="_blank" rel="noreferrer">
            View in Hub
          </a>
        )}
      </>
    );
  };

  const renderPublicTab = () => (
    <>
      {installError && (
        <div className="card card--error">
          <p className="error">{installError}</p>
          <button className="btn" type="button" onClick={() => setInstallError(null)}>
            Dismiss
          </button>
        </div>
      )}

      {publicPackagesQuery.isLoading && (
        <div className="card card--surface">
          <p>Loading hub packages...</p>
        </div>
      )}
      {publicPackagesQuery.isError && (
        <div className="card card--error">
          <p className="error">
            Unable to load hub packages: {publicErrorMessage ?? "Unknown error"}
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
            <p>No hub packages available yet.</p>
          </div>
        )}
      {!publicPackagesQuery.isLoading &&
        !publicPackagesQuery.isError &&
        publicPackages.length > 0 && (
          <div className="workflow-grid-shell">
            <div className="workflow-grid">
              {publicPackages.map((pkg) => (
                <PackageCard key={pkg.name} pkg={pkg} actionSlot={renderActions(pkg, "primary")} />
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
    if (!ownerFilter) {
      return (
        <div className="card card--surface">
          <p>Sign in to filter hub packages by owner.</p>
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
      <div className="workflow-grid-shell">
        <div className="workflow-grid">
          {myPackages.map((pkg) => (
            <PackageCard key={pkg.name} pkg={pkg} actionSlot={renderActions(pkg, "ghost")} />
          ))}
        </div>
      </div>
    );
  };

  const renderLocalTab = () => {
    if (!canViewLocalPackages) {
      return (
        <div className="card card--surface">
          <p>You need workflow.viewer or workflow.editor access to view local packages.</p>
        </div>
      );
    }
    if (localLoading) {
      return (
        <div className="card card--surface">
          <p>Loading local packages...</p>
        </div>
      );
    }
    if (localError) {
      return (
        <div className="card card--error">
          <p className="error">{localError}</p>
          <button className="btn" type="button" onClick={() => void loadLocalPackages()}>
            Retry
          </button>
        </div>
      );
    }
    if (localPackages.length === 0) {
      return (
        <div className="card card--surface">
          <p>No local packages installed yet.</p>
        </div>
      );
    }
    return (
      <div className="workflow-grid-shell">
        <div className="workflow-grid">
          {localPackages.map((pkg) => (
            <LocalPackageCard key={pkg.name} pkg={pkg} />
          ))}
        </div>
      </div>
    );
  };

  const heading =
    activeTab === "public" ? "Package Center" : activeTab === "mine" ? "My Packages" : "Installed Packages";
  const subheading =
    activeTab === "public"
      ? "Discover hub packages and install them into your workspace."
      : activeTab === "mine"
        ? "Review hub packages that match your owner profile."
        : "Review packages available in this workspace.";

  const publicCount = publicPackages?.length ?? 0;
  const myCount = myPackages?.length ?? 0;
  const localCount = localPackages?.length ?? 0;

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
            <span className="package-center-stat">
              Installed
              <span className="package-center-stat__value">
                {canViewLocalPackages ? localCount : "Locked"}
              </span>
            </span>
          </div>
        </div>
        <div className="package-center-hero__actions">
          {hubBrowseUrl && (
            <a className="btn btn--ghost" href={hubBrowseUrl} target="_blank" rel="noreferrer">
              Open Hub
              <ArrowUpRightIcon />
            </a>
          )}
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
        <button
          type="button"
          className={`package-center-tab ${activeTab === "local" ? "package-center-tab--active" : ""}`}
          onClick={() => handleTabChange("local")}
          disabled={!canViewLocalPackages}
          title={!canViewLocalPackages ? "Requires workflow.viewer access." : undefined}
        >
          Installed
        </button>
      </div>
      <div className="package-center-content">
        {activeTab === "public" ? renderPublicTab() : activeTab === "mine" ? renderMyTab() : renderLocalTab()}
      </div>
    </div>
  );
};

export default PackageCenterPage;
