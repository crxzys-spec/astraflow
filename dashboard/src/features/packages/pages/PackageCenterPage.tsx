import { useCallback, useEffect, useMemo, useState, type FormEvent, type ReactNode } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useHubAccount } from "../../../store/hubAccountSlice";
import { useHubPackages } from "../../../store/hubPackagesSlice";
import type { HubPackageSummaryModel } from "../../../services/hubPackages";
import {
  installHubPackage,
  publishHubPackageLocal,
  uninstallHubPackage,
} from "../../../services/hubPackages";
import { listPackages } from "../../../services/packages";
import { HubVisibility, type PackageSummary } from "../../../client/models";
import { useAuthStore } from "@store/authSlice";
import { useMessageCenter } from "../../../components/MessageCenter";
import { getHubBrowseUrl, getHubItemUrl } from "../../../lib/hubLinks";
import { resolveApiErrorMessage } from "../../../lib/apiErrors";
import { resolveLocalizedText } from "../../../lib/manifestText";
import { useTranslation } from "react-i18next";

const getErrorMessage = (error: unknown, fallback: string): string =>
  resolveApiErrorMessage(error, fallback);

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

const resolveDefaultVersion = (pkg?: PackageSummary | null) =>
  pkg?.latestVersion ?? pkg?.defaultVersion ?? pkg?.versions?.[0] ?? "";

const LOCAL_PACKAGE_OWNER = "local";

const resolveLocalPackageOwner = (pkg: PackageSummary) => {
  const owner = (pkg.ownerId ?? pkg.hub?.ownerId ?? "").trim();
  if (!owner || owner === LOCAL_PACKAGE_OWNER) {
    return null;
  }
  return owner;
};

const resolveLocalPackageRef = (pkg: PackageSummary) => {
  const owner = resolveLocalPackageOwner(pkg);
  if (!owner) {
    return pkg.name;
  }
  return `${owner}/${pkg.name}`;
};

const resolveLocalOwnerLabel = (pkg: PackageSummary) => {
  const owner = (pkg.hub?.ownerName ?? pkg.hub?.ownerId ?? pkg.ownerId ?? "").trim();
  if (!owner || owner === LOCAL_PACKAGE_OWNER) {
    return null;
  }
  return owner;
};

const resolveLocalUninstallOwner = (pkg: PackageSummary) => {
  const owner = (pkg.ownerId ?? pkg.hub?.ownerId ?? "").trim();
  if (!owner || owner === LOCAL_PACKAGE_OWNER) {
    return null;
  }
  return owner;
};

const PackageCard = ({
  pkg,
  actionSlot,
}: {
  pkg: HubPackageSummaryModel;
  actionSlot?: ReactNode;
}) => {
  const { t } = useTranslation();
  const visibilityValue = pkg.visibility ?? "public";
  const visibilityLabels: Record<string, string> = {
    public: t("packages.visibility.public"),
    private: t("packages.visibility.private"),
    internal: t("packages.visibility.internal"),
  };
  const visibilityLabel = visibilityLabels[visibilityValue] ?? visibilityValue;
  const ownerDisplay = pkg.ownerName ?? pkg.ownerId ?? t("common.unassigned");
  const latestVersionLabel = pkg.latestVersion ?? t("packages.latest");
  const packageName = pkg.name;
  const description =
    resolveLocalizedText(pkg.description) || t("packages.card.descriptionFallback");
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
              <span className="workflow-card__placeholder-title">
                {t("packages.card.previewHubTitle")}
              </span>
              <span className="workflow-card__placeholder-subtitle">
                {t("packages.card.previewHubSubtitle")}
              </span>
            </div>
          </div>
        </div>
        <header className="workflow-card__header">
          <div className="workflow-card__identity">
            <small className="workflow-card__eyebrow">{t("packages.card.hubPackage")}</small>
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
            <span>{t("packages.card.signatureLabel")}</span>
            <code>{pkg.name}</code>
          </div>
        </footer>
      </div>
    </article>
  );
};

const LocalPackageCard = ({
  pkg,
  actionSlot,
}: {
  pkg: PackageSummary;
  actionSlot?: ReactNode;
}) => {
  const { t } = useTranslation();
  const hubMeta = pkg.hub ?? null;
  const visibilityValue = hubMeta?.visibility ?? "local";
  const visibilityLabels: Record<string, string> = {
    public: t("packages.visibility.public"),
    private: t("packages.visibility.private"),
    internal: t("packages.visibility.internal"),
    local: t("packages.visibility.local"),
  };
  const visibilityLabel = visibilityLabels[visibilityValue] ?? visibilityValue;
  const ownerDisplay = resolveLocalOwnerLabel(pkg) ?? t("common.local");
  const latestVersionLabel =
    pkg.latestVersion ?? pkg.defaultVersion ?? pkg.versions?.[0] ?? t("packages.localVersion");
  const packageRef = resolveLocalPackageRef(pkg);
  const packageName = pkg.name;
  const description =
    resolveLocalizedText(pkg.description) ||
    (hubMeta
      ? t("packages.card.linkedDescription", {
          name: hubMeta.hubName,
          version: hubMeta.hubVersion,
        })
      : t("packages.card.localDescriptionFallback"));
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
              <span className="workflow-card__placeholder-title">
                {t("packages.card.previewLocalTitle")}
              </span>
              <span className="workflow-card__placeholder-subtitle">
                {t("packages.card.previewLocalSubtitle")}
              </span>
            </div>
          </div>
        </div>
        <header className="workflow-card__header">
          <div className="workflow-card__identity">
            <small className="workflow-card__eyebrow">{t("packages.card.localPackage")}</small>
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
            <span>{t("packages.card.signatureLabel")}</span>
            <code>{packageRef}</code>
          </div>
        </footer>
      </div>
    </article>
  );
};

const PackageCenterPage = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const canInstall = useAuthStore((state) => state.hasRole(["admin", "workflow.editor"]));
  const canViewOwnPackages = useAuthStore((state) =>
    state.hasRole(["admin", "workflow.editor", "workflow.viewer"])
  );
  const canViewLocalPackages = useAuthStore((state) =>
    state.hasRole(["admin", "workflow.editor", "workflow.viewer"])
  );
  const canPublishHub = useAuthStore((state) => state.hasRole(["admin", "workflow.editor"]));
  const { pushMessage } = useMessageCenter();
  const hubBrowseUrl = getHubBrowseUrl("packages");
  const hubAccountQuery = useHubAccount({ enabled: canViewOwnPackages });
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
  const [activeUninstallName, setActiveUninstallName] = useState<string | null>(null);
  const [uninstallError, setUninstallError] = useState<string | null>(null);
  const [localPackages, setLocalPackages] = useState<PackageSummary[]>([]);
  const [localLoading, setLocalLoading] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);
  const [localLoaded, setLocalLoaded] = useState(false);
  const [publishOpen, setPublishOpen] = useState(false);
  const [publishLoading, setPublishLoading] = useState(false);
  const [publishError, setPublishError] = useState<string | null>(null);
  const [publishPackageName, setPublishPackageName] = useState("");
  const [publishPackageVersion, setPublishPackageVersion] = useState("");
  const [publishForm, setPublishForm] = useState({
    summary: "",
    readme: "",
    tags: "",
    visibility: HubVisibility.Private,
  });

  const ownerFilter = hubAccountQuery.account?.id ?? null;
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
  const hubAccountErrorMessage = hubAccountQuery.error
    ? getErrorMessage(hubAccountQuery.error, t("packages.errors.loadAccountFallback"))
    : null;

  const resolveHubPackageRef = (pkg: HubPackageSummaryModel) => {
    const owner = (pkg.ownerId ?? pkg.ownerName ?? "").trim();
    if (!owner) {
      return pkg.name;
    }
    return `${owner}/${pkg.name}`;
  };

  const resolveHubPackageOwnerId = (pkg: HubPackageSummaryModel) =>
    (pkg.ownerId ?? "").trim();

  const installedHubPackages = useMemo(() => {
    const index = new Map<string, { versions: Set<string>; ownerId: string }>();
    localPackages.forEach((pkg) => {
      const hubName = pkg.hub?.hubName?.trim();
      const ownerId = (pkg.ownerId ?? "").trim() || LOCAL_PACKAGE_OWNER;
      const ref =
        hubName ||
        (ownerId && ownerId !== LOCAL_PACKAGE_OWNER ? `${ownerId}/${pkg.name}` : "");
      if (!ref) {
        return;
      }
      const entry = index.get(ref) ?? { versions: new Set<string>(), ownerId };
      (pkg.versions ?? []).forEach((version) => {
        if (version) {
          entry.versions.add(version);
        }
      });
      if (pkg.hub?.hubVersion) {
        entry.versions.add(pkg.hub.hubVersion);
      }
      if (!entry.versions.size && pkg.latestVersion) {
        entry.versions.add(pkg.latestVersion);
      }
      index.set(ref, entry);
    });
    return index;
  }, [localPackages]);

  const resolveInstallState = (pkg: HubPackageSummaryModel) => {
    const ownerId = resolveHubPackageOwnerId(pkg);
    if (!ownerId) {
      return { status: "unknown" as const };
    }
    const ref = `${ownerId}/${pkg.name}`;
    const entry = installedHubPackages.get(ref);
    if (!entry || entry.versions.size === 0) {
      return { status: "install" as const };
    }
    const latestVersion = pkg.latestVersion ?? "";
    if (latestVersion && !entry.versions.has(latestVersion)) {
      return { status: "update" as const };
    }
    return { status: "installed" as const };
  };

  const handleInstall = (pkg: HubPackageSummaryModel) => {
    if (!canInstall) {
      setInstallError(t("packages.permissions.install"));
      return;
    }
    const ownerId = resolveHubPackageOwnerId(pkg);
    if (!ownerId) {
      setInstallError(t("packages.errors.missingOwner"));
      return;
    }
    const packageRef = resolveHubPackageRef(pkg);
    const payload = pkg.latestVersion ? { version: pkg.latestVersion } : undefined;
    setActiveInstallName(packageRef);
    setInstallError(null);
    setUninstallError(null);
    installHubPackage(ownerId, pkg.name, payload)
      .then((response) => {
        pushMessage({
          tone: "success",
          content: t("packages.installSuccess", {
            name: response.name,
            version: response.version,
          }),
        });
        void loadLocalPackages();
      })
      .catch((error) => {
        setInstallError(getErrorMessage(error, t("packages.errors.install")));
      })
      .finally(() => {
        setActiveInstallName(null);
      });
  };

  const handleUninstall = (pkg: PackageSummary) => {
    if (!canInstall) {
      setUninstallError(t("packages.permissions.uninstall"));
      return;
    }
    const ownerId = resolveLocalUninstallOwner(pkg);
    if (!ownerId) {
      setUninstallError(t("packages.errors.localManaged"));
      return;
    }
    const packageRef = resolveLocalPackageRef(pkg);
    const versions = pkg.versions ?? [];
    const payload = versions.length === 1 ? { version: versions[0] } : undefined;
    setActiveUninstallName(packageRef);
    setUninstallError(null);
    setInstallError(null);
    uninstallHubPackage(ownerId, pkg.name, payload)
      .then((response) => {
        const versionLabel = response.version && response.version !== "all"
          ? response.version
          : t("packages.allVersions");
        pushMessage({
          tone: "success",
          content: t("packages.uninstallSuccess", {
            name: response.name,
            version: versionLabel,
          }),
        });
        void loadLocalPackages();
      })
      .catch((error) => {
        setUninstallError(getErrorMessage(error, t("packages.errors.uninstall")));
      })
      .finally(() => {
        setActiveUninstallName(null);
      });
  };

  const loadLocalPackages = useCallback(async () => {
    setLocalLoading(true);
    setLocalError(null);
    try {
      const items = await listPackages();
      const sorted = [...items].sort((a, b) => resolveLocalPackageRef(a).localeCompare(resolveLocalPackageRef(b)));
      setLocalPackages(sorted);
    } catch (error) {
      setLocalError(getErrorMessage(error, t("packages.errors.loadLocal")));
    } finally {
      setLocalLoading(false);
      setLocalLoaded(true);
    }
  }, []);

  useEffect(() => {
    if (!canViewLocalPackages || localLoaded || localLoading) {
      return;
    }
    void loadLocalPackages();
  }, [canViewLocalPackages, localLoaded, localLoading, loadLocalPackages]);

  const visibilityOptions: HubVisibility[] = [
    HubVisibility.Private,
    HubVisibility.Internal,
    HubVisibility.Public,
  ];

  const parseTags = (value: string) =>
    value
      .split(",")
      .map((tag) => tag.trim())
      .filter(Boolean);

  const publishablePackages = useMemo(
    () => localPackages.filter((pkg) => !pkg.ownerId || pkg.ownerId === LOCAL_PACKAGE_OWNER),
    [localPackages],
  );

  const openPublishModal = () => {
    setPublishForm({
      summary: "",
      readme: "",
      tags: "",
      visibility: HubVisibility.Private,
    });
    const defaultPackage = publishablePackages[0];
    setPublishPackageName(defaultPackage?.name ?? "");
    setPublishPackageVersion(resolveDefaultVersion(defaultPackage));
    setPublishOpen(true);
    setPublishError(null);
    if (!publishablePackages.length && !localLoading) {
      void loadLocalPackages();
    }
  };

  const closePublishModal = () => {
    setPublishOpen(false);
    setPublishError(null);
    setPublishPackageName("");
    setPublishPackageVersion("");
  };

  const handlePublishSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!publishPackageName) {
      setPublishError(t("packages.publish.selectPackage"));
      return;
    }
    if (!publishPackageVersion) {
      setPublishError(t("packages.publish.selectVersion"));
      return;
    }
    setPublishLoading(true);
    setPublishError(null);
    const tags = parseTags(publishForm.tags);
    try {
      const result = await publishHubPackageLocal({
        name: publishPackageName,
        version: publishPackageVersion,
        visibility: publishForm.visibility,
        summary: publishForm.summary.trim() || undefined,
        readme: publishForm.readme.trim() || undefined,
        tags: tags.length ? tags : undefined,
      });
      pushMessage({
        tone: "success",
        content: t("packages.publish.success", { name: result.name, version: result.version }),
      });
      setPublishOpen(false);
      setPublishPackageName("");
      setPublishPackageVersion("");
      setPublishForm((prev) => ({
        ...prev,
        summary: "",
        readme: "",
        tags: "",
      }));
      publicPackagesQuery.refetch();
      if (ownerFilter) {
        myPackagesQuery.refetch();
      }
    } catch (error) {
      setPublishError(getErrorMessage(error, t("packages.errors.publish")));
    } finally {
      setPublishLoading(false);
    }
  };

  useEffect(() => {
    if (activeTab !== "local" || !canViewLocalPackages || localLoaded || localLoading) {
      return;
    }
    void loadLocalPackages();
  }, [activeTab, canViewLocalPackages, localLoaded, localLoading, loadLocalPackages]);

  useEffect(() => {
    if (!publishOpen) {
      return;
    }
    if (!publishablePackages.length) {
      return;
    }
    const selected =
      publishablePackages.find((pkg) => pkg.name === publishPackageName) ?? publishablePackages[0];
    if (selected && publishPackageName !== selected.name) {
      setPublishPackageName(selected.name);
    }
    if (selected && !selected.versions?.includes(publishPackageVersion)) {
      setPublishPackageVersion(resolveDefaultVersion(selected));
    }
  }, [
    publishOpen,
    publishPackageName,
    publishPackageVersion,
    publishablePackages,
  ]);

  const renderActions = (pkg: HubPackageSummaryModel, variant: "primary" | "ghost") => {
    const packageRef = resolveHubPackageRef(pkg);
    const hubItemUrl = getHubItemUrl("packages", packageRef) ?? hubBrowseUrl;
    const installState = resolveInstallState(pkg);
    const installLabel =
      installState.status === "installed"
        ? t("packages.actions.installed")
        : installState.status === "update"
          ? t("packages.actions.update")
          : t("packages.actions.install");
    const installTone =
      installState.status === "installed"
        ? "btn--ghost"
        : variant === "primary"
          ? "btn--primary"
          : "btn--ghost";
    const disableInstall =
      !canInstall ||
      activeInstallName === packageRef ||
      activeUninstallName === packageRef ||
      installState.status === "installed";
    return (
      <>
        <button
          className={`btn ${installTone}`}
          type="button"
          onClick={() => handleInstall(pkg)}
          disabled={disableInstall}
        >
          {activeInstallName === packageRef ? t("packages.actions.installing") : installLabel}
        </button>
        {hubItemUrl && (
          <a className="btn btn--ghost" href={hubItemUrl} target="_blank" rel="noreferrer">
            {t("packages.actions.viewInHub")}
          </a>
        )}
      </>
    );
  };

  const renderActionErrors = () => (
    <>
      {installError && (
        <div className="card card--error">
          <p className="error">{installError}</p>
          <button className="btn" type="button" onClick={() => setInstallError(null)}>
            {t("common.dismiss")}
          </button>
        </div>
      )}
      {uninstallError && (
        <div className="card card--error">
          <p className="error">{uninstallError}</p>
          <button className="btn" type="button" onClick={() => setUninstallError(null)}>
            {t("common.dismiss")}
          </button>
        </div>
      )}
    </>
  );

  const renderLocalActions = (pkg: PackageSummary) => {
    const ownerId = resolveLocalUninstallOwner(pkg);
    if (!ownerId) {
      return null;
    }
    const packageRef = resolveLocalPackageRef(pkg);
    const disableUninstall =
      !canInstall || activeUninstallName === packageRef || activeInstallName === packageRef;
    return (
      <button
        className="btn btn--ghost"
        type="button"
        onClick={() => handleUninstall(pkg)}
        disabled={disableUninstall}
      >
        {activeUninstallName === packageRef
          ? t("packages.actions.uninstalling")
          : t("packages.actions.uninstall")}
      </button>
    );
  };

  const renderPublicTab = () => (
    <>
      {publicPackagesQuery.isLoading && (
        <div className="card card--surface">
          <p>{t("packages.loading.hubPackages")}</p>
        </div>
      )}
      {publicPackagesQuery.isError && (
        <div className="card card--error">
          <p className="error">
            {t("packages.errors.loadHub", {
              message: publicErrorMessage ?? t("common.unknownError"),
            })}
          </p>
          <button className="btn" type="button" onClick={() => publicPackagesQuery.refetch()}>
            {t("common.retry")}
          </button>
        </div>
      )}
      {!publicPackagesQuery.isLoading &&
        !publicPackagesQuery.isError &&
        publicPackages.length === 0 && (
          <div className="card card--surface">
            <p>{t("packages.empty.public")}</p>
          </div>
        )}
      {!publicPackagesQuery.isLoading &&
        !publicPackagesQuery.isError &&
        publicPackages.length > 0 && (
          <div className="workflow-grid-shell">
            <div className="workflow-grid">
              {publicPackages.map((pkg) => (
                <PackageCard
                  key={resolveHubPackageRef(pkg)}
                  pkg={pkg}
                  actionSlot={renderActions(pkg, "primary")}
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
          <p>{t("packages.permissions.viewMine")}</p>
        </div>
      );
    }
    if (hubAccountQuery.isLoading) {
      return (
        <div className="card card--surface">
          <p>{t("packages.loading.hubAccount")}</p>
        </div>
      );
    }
    if (hubAccountQuery.isError) {
      return (
        <div className="card card--error">
          <p className="error">
            {t("packages.errors.loadAccount", {
              message: hubAccountErrorMessage ?? t("common.unknownError"),
            })}
          </p>
          <button className="btn" type="button" onClick={() => hubAccountQuery.refetch()}>
            {t("common.retry")}
          </button>
        </div>
      );
    }
    if (!ownerFilter) {
      return (
        <div className="card card--surface">
          <p>{t("packages.empty.noAccount")}</p>
        </div>
      );
    }
    if (myPackagesQuery.isLoading) {
      return (
        <div className="card card--surface">
          <p>{t("packages.loading.myPackages")}</p>
        </div>
      );
    }
    if (myPackagesQuery.isError) {
      return (
        <div className="card card--error">
          <p className="error">
            {t("packages.errors.loadMine", {
              message: myErrorMessage ?? t("common.unknownError"),
            })}
          </p>
          <button className="btn" type="button" onClick={() => myPackagesQuery.refetch()}>
            {t("common.retry")}
          </button>
        </div>
      );
    }
    if (myPackages.length === 0) {
      return (
        <div className="card card--surface">
          <p>{t("packages.empty.mine")}</p>
        </div>
      );
    }
    return (
      <div className="workflow-grid-shell">
        <div className="workflow-grid">
          {myPackages.map((pkg) => (
            <PackageCard
              key={resolveHubPackageRef(pkg)}
              pkg={pkg}
              actionSlot={renderActions(pkg, "ghost")}
            />
          ))}
        </div>
      </div>
    );
  };

  const renderLocalTab = () => {
    if (!canViewLocalPackages) {
      return (
        <div className="card card--surface">
          <p>{t("packages.permissions.viewLocal")}</p>
        </div>
      );
    }
    if (localLoading) {
      return (
        <div className="card card--surface">
          <p>{t("packages.loading.localPackages")}</p>
        </div>
      );
    }
    if (localError) {
      return (
        <div className="card card--error">
          <p className="error">{localError}</p>
          <button className="btn" type="button" onClick={() => void loadLocalPackages()}>
            {t("common.retry")}
          </button>
        </div>
      );
    }
    if (localPackages.length === 0) {
      return (
        <div className="card card--surface">
          <p>{t("packages.empty.local")}</p>
        </div>
      );
    }
    return (
      <div className="workflow-grid-shell">
        <div className="workflow-grid">
          {localPackages.map((pkg) => (
            <LocalPackageCard
              key={resolveLocalPackageRef(pkg)}
              pkg={pkg}
              actionSlot={renderLocalActions(pkg)}
            />
          ))}
        </div>
      </div>
    );
  };

  const heading =
    activeTab === "public"
      ? t("packages.heading.public")
      : activeTab === "mine"
        ? t("packages.heading.mine")
        : t("packages.heading.local");
  const subheading =
    activeTab === "public"
      ? t("packages.subheading.public")
      : activeTab === "mine"
        ? t("packages.subheading.mine")
        : t("packages.subheading.local");

  const publicCount = publicPackages?.length ?? 0;
  const myCount = ownerFilter ? myPackages?.length ?? 0 : 0;
  const localCount = localPackages?.length ?? 0;
  const myCountLabel = !canViewOwnPackages
    ? t("packages.stats.locked")
    : hubAccountQuery.isLoading
      ? t("packages.stats.loading")
      : hubAccountQuery.isError || !ownerFilter
        ? t("packages.stats.unavailable")
        : myCount;
  const selectedPublishPackage =
    publishablePackages.find((pkg) => pkg.name === publishPackageName) ?? null;
  const publishVersionOptions = selectedPublishPackage?.versions ?? [];

  return (
    <div className="card stack package-center-panel">
      <header className="package-center-hero">
        <div className="package-center-hero__text">
          <p className="package-center-hero__eyebrow">{t("packages.eyebrow")}</p>
          <h2>{heading}</h2>
          <p className="text-subtle">{subheading}</p>
          <div className="package-center-stats">
            <span className="package-center-stat">
              {t("packages.stats.public")}
              <span className="package-center-stat__value">{publicCount}</span>
            </span>
            <span className="package-center-stat">
              {t("packages.stats.hubAccount")}
              <span className="package-center-stat__value">{myCountLabel}</span>
            </span>
            <span className="package-center-stat">
              {t("packages.stats.installed")}
              <span className="package-center-stat__value">
                {canViewLocalPackages ? localCount : t("packages.stats.locked")}
              </span>
            </span>
          </div>
        </div>
        <div className="package-center-hero__actions">
          {hubBrowseUrl && (
            <a className="btn btn--ghost" href={hubBrowseUrl} target="_blank" rel="noreferrer">
              {t("common.openHub")}
              <ArrowUpRightIcon />
            </a>
          )}
          {canPublishHub && (
            <button type="button" className="btn" onClick={openPublishModal}>
              {t("packages.actions.publishPackage")}
            </button>
          )}
          <button
            type="button"
            className="btn btn--ghost"
            onClick={() => navigate("/workflows/new")}
            title={t("packages.actions.createWorkflowTitle")}
          >
            {t("packages.actions.createWorkflow")}
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
          {t("packages.tabs.discover")}
        </button>
        <button
          type="button"
          className={`package-center-tab ${activeTab === "mine" ? "package-center-tab--active" : ""}`}
          onClick={() => handleTabChange("mine")}
          disabled={!canViewOwnPackages}
          title={!canViewOwnPackages ? t("packages.permissions.tabRequiresViewer") : undefined}
        >
          {t("packages.tabs.hubAccount")}
        </button>
        <button
          type="button"
          className={`package-center-tab ${activeTab === "local" ? "package-center-tab--active" : ""}`}
          onClick={() => handleTabChange("local")}
          disabled={!canViewLocalPackages}
          title={!canViewLocalPackages ? t("packages.permissions.tabRequiresViewer") : undefined}
        >
          {t("packages.tabs.installed")}
        </button>
      </div>
      <div className="package-center-content">
        {renderActionErrors()}
        {activeTab === "public" ? renderPublicTab() : activeTab === "mine" ? renderMyTab() : renderLocalTab()}
      </div>
      {publishOpen && (
        <div className="modal">
          <div className="modal__backdrop" onClick={closePublishModal} />
          <form className="modal__panel card publish-modal" onSubmit={handlePublishSubmit}>
            <header className="modal__header">
              <div>
                <h3>{t("packages.publish.title")}</h3>
                <p className="text-subtle">{t("packages.publish.subtitle")}</p>
              </div>
              <button
                className="modal__close"
                type="button"
                onClick={closePublishModal}
                aria-label={t("packages.publish.close")}
              >
                x
              </button>
            </header>
            <div className="publish-modal__grid">
              <label className="form-field publish-modal__field">
                <span>{t("packages.publish.packageLabel")}</span>
                <select
                  value={publishPackageName}
                  onChange={(event) => setPublishPackageName(event.target.value)}
                  disabled={localLoading || publishablePackages.length === 0}
                >
                  {publishablePackages.map((pkg) => (
                    <option key={pkg.name} value={pkg.name}>
                      {pkg.name}
                    </option>
                  ))}
                </select>
                {localLoading && (
                  <small className="publish-modal__helper">{t("packages.loading.localPackages")}</small>
                )}
                {!localLoading && publishablePackages.length === 0 && (
                  <small className="publish-modal__helper">{t("packages.publish.noneReady")}</small>
                )}
              </label>
              <label className="form-field publish-modal__field">
                <span>{t("packages.publish.versionLabel")}</span>
                <select
                  value={publishPackageVersion}
                  onChange={(event) => setPublishPackageVersion(event.target.value)}
                  disabled={!publishPackageName || publishVersionOptions.length === 0}
                >
                  {publishVersionOptions.map((version) => (
                    <option key={version} value={version}>
                      {version}
                    </option>
                  ))}
                </select>
              </label>
              <label className="form-field publish-modal__field">
                <span>{t("packages.publish.visibilityLabel")}</span>
                <select
                  value={publishForm.visibility}
                  onChange={(event) =>
                    setPublishForm((prev) => ({
                      ...prev,
                      visibility: event.target.value as HubVisibility,
                    }))
                  }
                >
                  {visibilityOptions.map((option) => (
                    <option key={option} value={option}>
                      {t(`packages.visibility.${option}`)}
                    </option>
                  ))}
                </select>
              </label>
              <label className="form-field publish-modal__field">
                <span>{t("packages.publish.tagsLabel")}</span>
                <input
                  type="text"
                  value={publishForm.tags}
                  onChange={(event) =>
                    setPublishForm((prev) => ({ ...prev, tags: event.target.value }))
                  }
                />
              </label>
              <label className="form-field publish-modal__field publish-modal__field--full">
                <span>{t("packages.publish.summaryLabel")}</span>
                <textarea
                  rows={3}
                  value={publishForm.summary}
                  onChange={(event) =>
                    setPublishForm((prev) => ({ ...prev, summary: event.target.value }))
                  }
                />
              </label>
              <label className="form-field publish-modal__field publish-modal__field--full">
                <span>{t("packages.publish.readmeLabel")}</span>
                <textarea
                  rows={6}
                  value={publishForm.readme}
                  onChange={(event) =>
                    setPublishForm((prev) => ({ ...prev, readme: event.target.value }))
                  }
                />
              </label>
            </div>
            {publishError && <p className="error">{publishError}</p>}
            <footer className="modal__footer">
              <button className="btn btn--ghost" type="button" onClick={closePublishModal}>
                {t("packages.publish.cancel")}
              </button>
              <button className="btn" type="submit" disabled={publishLoading}>
                {publishLoading ? t("packages.publish.publishing") : t("packages.publish.publish")}
              </button>
            </footer>
          </form>
        </div>
      )}
    </div>
  );
};

export default PackageCenterPage;
