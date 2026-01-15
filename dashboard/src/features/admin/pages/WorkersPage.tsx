import { useMemo, useState } from "react";
import type { TFunction } from "i18next";
import { useTranslation } from "react-i18next";
import type { WorkerPackageStatus } from "../../../client/models";
import { useAuthStore } from "@store/authSlice";
import { useWorkers } from "@store/workersSlice";
import type { WorkerModel } from "../../../services/workers";

type FilterState = {
  search: string;
  queue: string;
  packageName: string;
  connection: "all" | "connected" | "disconnected";
  health: "all" | "healthy" | "unhealthy";
  packageStatus: "all" | WorkerPackageStatus;
};

const DEFAULT_FILTERS: FilterState = {
  search: "",
  queue: "",
  packageName: "",
  connection: "all",
  health: "all",
  packageStatus: "all",
};

const formatAge = (iso: string | null | undefined, t: TFunction) => {
  if (!iso) {
    return "-";
  }
  const timestamp = Date.parse(iso);
  if (Number.isNaN(timestamp)) {
    return "-";
  }
  const diffMs = Date.now() - timestamp;
  if (diffMs < 0) {
    return t("admin.workersPage.age.justNow");
  }
  const seconds = Math.floor(diffMs / 1000);
  if (seconds < 60) {
    return t("admin.workersPage.age.seconds", { count: seconds });
  }
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) {
    return t("admin.workersPage.age.minutes", { count: minutes });
  }
  const hours = Math.floor(minutes / 60);
  if (hours < 24) {
    return t("admin.workersPage.age.hours", { count: hours });
  }
  const days = Math.floor(hours / 24);
  return t("admin.workersPage.age.days", { count: days });
};

const formatPct = (value?: number | null) => {
  if (value == null || Number.isNaN(value)) {
    return "-";
  }
  return `${value.toFixed(1)}%`;
};

const formatMetric = (value?: number | null) => {
  if (value == null || Number.isNaN(value)) {
    return "-";
  }
  return `${Math.round(value)}`;
};

const formatLatency = (value?: number | null) => {
  if (value == null || Number.isNaN(value)) {
    return "-";
  }
  return `${Math.round(value)}ms`;
};

const summarizePackages = (worker: WorkerModel) => {
  const packages = worker.packages ?? [];
  if (!packages.length) {
    return { chips: [], extra: 0 };
  }
  const chips = packages
    .slice(0, 3)
    .map((pkg) => pkg.name ?? "unknown")
    .filter(Boolean);
  return { chips, extra: Math.max(0, packages.length - chips.length) };
};

const WorkersPage = () => {
  const isAdmin = useAuthStore((state) => state.hasRole(["admin"]));
  const { t } = useTranslation();
  const [filters, setFilters] = useState<FilterState>(DEFAULT_FILTERS);

  const queryParams = useMemo(
    () => ({
      queue: filters.queue.trim() || undefined,
      connected: filters.connection === "all" ? undefined : filters.connection === "connected",
      healthy: filters.health === "all" ? undefined : filters.health === "healthy",
      packageName: filters.packageName.trim() || undefined,
      packageStatus: filters.packageStatus === "all" ? undefined : filters.packageStatus,
      limit: 200,
    }),
    [filters],
  );

  const { items, status, error, refetch } = useWorkers(queryParams, { enabled: isAdmin });

  const visibleItems = useMemo(() => {
    const search = filters.search.trim().toLowerCase();
    if (!search) {
      return items;
    }
    return items.filter((worker) => {
      const name = worker.id?.toLowerCase() ?? "";
      const host = worker.hostname?.toLowerCase() ?? "";
      const tenant = worker.tenant?.toLowerCase() ?? "";
      return name.includes(search) || host.includes(search) || tenant.includes(search);
    });
  }, [filters.search, items]);

  const stats = useMemo(() => {
    const connected = items.filter((worker) => worker.connected).length;
    const registered = items.filter((worker) => worker.registered).length;
    const healthy = items.filter((worker) => worker.heartbeat?.healthy).length;
    return {
      total: items.length,
      connected,
      registered,
      healthy,
    };
  }, [items]);

  if (!isAdmin) {
    return (
      <div className="admin-view">
        <div className="card stack admin-panel">
          <h2>{t("admin.workersPage.accessDeniedTitle")}</h2>
          <p className="text-subtle">{t("admin.workersPage.accessDeniedMessage")}</p>
        </div>
      </div>
    );
  }

  const clearFilters = () => setFilters(DEFAULT_FILTERS);

  return (
    <div className="admin-view">
      <div className="card stack admin-panel">
        <header className="card__header worker-header admin-panel__header">
          <div>
            <span className="admin-panel__eyebrow">{t("admin.eyebrow")}</span>
            <h2>{t("admin.workersPage.title")}</h2>
            <p className="text-subtle admin-panel__description">{t("admin.workersPage.subtitle")}</p>
          </div>
          <div className="builder-actions builder-actions--buttons">
            <button className="btn btn--ghost" type="button" onClick={clearFilters}>
              {t("admin.workersPage.actions.clearFilters")}
            </button>
            <button className="btn" type="button" onClick={() => void refetch()} disabled={status === "loading"}>
              {status === "loading" ? t("admin.workersPage.actions.refreshing") : t("common.refresh")}
            </button>
          </div>
        </header>

        <div className="admin-section admin-section--stats worker-stats">
          <div className="worker-stat">
            <span className="worker-stat__label">{t("admin.workersPage.stats.total")}</span>
            <span className="worker-stat__value">{stats.total}</span>
          </div>
          <div className="worker-stat">
            <span className="worker-stat__label">{t("admin.workersPage.stats.connected")}</span>
            <span className="worker-stat__value">{stats.connected}</span>
          </div>
          <div className="worker-stat">
            <span className="worker-stat__label">{t("admin.workersPage.stats.registered")}</span>
            <span className="worker-stat__value">{stats.registered}</span>
          </div>
          <div className="worker-stat">
            <span className="worker-stat__label">{t("admin.workersPage.stats.healthy")}</span>
            <span className="worker-stat__value">{stats.healthy}</span>
          </div>
        </div>

        <form className="admin-section admin-section--filters">
          <div className="builder-grid" style={{ gridTemplateColumns: "repeat(auto-fit,minmax(220px,1fr))" }}>
            <label className="stack">
              <span>{t("admin.workersPage.filters.search")}</span>
              <input
                type="text"
                value={filters.search}
                onChange={(evt) => setFilters((prev) => ({ ...prev, search: evt.target.value }))}
                placeholder={t("admin.workersPage.filters.searchPlaceholder")}
              />
            </label>
            <label className="stack">
              <span>{t("admin.workersPage.filters.queue")}</span>
              <input
                type="text"
                value={filters.queue}
                onChange={(evt) => setFilters((prev) => ({ ...prev, queue: evt.target.value }))}
                placeholder={t("admin.workersPage.filters.queuePlaceholder")}
              />
            </label>
            <label className="stack">
              <span>{t("admin.workersPage.filters.connection")}</span>
              <select
                value={filters.connection}
                onChange={(evt) => setFilters((prev) => ({ ...prev, connection: evt.target.value as FilterState["connection"] }))}
              >
                <option value="all">{t("admin.workersPage.filters.all")}</option>
                <option value="connected">{t("admin.workersPage.filters.connected")}</option>
                <option value="disconnected">{t("admin.workersPage.filters.disconnected")}</option>
              </select>
            </label>
            <label className="stack">
              <span>{t("admin.workersPage.filters.health")}</span>
              <select
                value={filters.health}
                onChange={(evt) => setFilters((prev) => ({ ...prev, health: evt.target.value as FilterState["health"] }))}
              >
                <option value="all">{t("admin.workersPage.filters.all")}</option>
                <option value="healthy">{t("admin.workersPage.filters.healthy")}</option>
                <option value="unhealthy">{t("admin.workersPage.filters.unhealthy")}</option>
              </select>
            </label>
            <label className="stack">
              <span>{t("admin.workersPage.filters.package")}</span>
              <input
                type="text"
                value={filters.packageName}
                onChange={(evt) => setFilters((prev) => ({ ...prev, packageName: evt.target.value }))}
                placeholder={t("admin.workersPage.filters.packagePlaceholder")}
              />
            </label>
            <label className="stack">
              <span>{t("admin.workersPage.filters.packageStatus")}</span>
              <select
                value={filters.packageStatus}
                onChange={(evt) =>
                  setFilters((prev) => ({ ...prev, packageStatus: evt.target.value as FilterState["packageStatus"] }))
                }
              >
                <option value="all">{t("admin.workersPage.filters.all")}</option>
                <option value="installed">{t("admin.workersPage.packageStatus.installed")}</option>
                <option value="installing">{t("admin.workersPage.packageStatus.installing")}</option>
                <option value="uninstalling">{t("admin.workersPage.packageStatus.uninstalling")}</option>
                <option value="removed">{t("admin.workersPage.packageStatus.removed")}</option>
                <option value="failed">{t("admin.workersPage.packageStatus.failed")}</option>
                <option value="missing">{t("admin.workersPage.packageStatus.missing")}</option>
                <option value="unknown">{t("admin.workersPage.packageStatus.unknown")}</option>
              </select>
            </label>
          </div>
        </form>

        {status === "error" && (
          <div className="admin-section admin-section--notice stack">
            <p className="error">
              {t("admin.workersPage.messages.loadError", { message: error?.message ?? t("common.unknownError") })}
            </p>
            <button className="btn" type="button" onClick={() => void refetch()}>
              {t("common.retry")}
            </button>
          </div>
        )}

        <div className="admin-section admin-section--table">
          <div className="admin-table-wrap">
            <table className="data-table worker-table admin-table">
              <thead>
                <tr>
                  <th>{t("admin.workersPage.table.worker")}</th>
                  <th>{t("admin.workersPage.table.status")}</th>
                  <th>{t("admin.workersPage.table.heartbeat")}</th>
                  <th>{t("admin.workersPage.table.queues")}</th>
                  <th>{t("admin.workersPage.table.packages")}</th>
                  <th>{t("admin.workersPage.table.metrics")}</th>
                </tr>
              </thead>
              <tbody>
                {status === "loading" ? (
                  <tr>
                    <td colSpan={6}>{t("admin.workersPage.messages.loading")}</td>
                  </tr>
                ) : visibleItems.length === 0 ? (
                  <tr>
                    <td colSpan={6}>{t("admin.workersPage.messages.empty")}</td>
                  </tr>
                ) : (
                  visibleItems.map((worker) => {
                    const heartbeat = worker.heartbeat;
                    const metrics = heartbeat?.metrics;
                    const packages = summarizePackages(worker);
                    return (
                      <tr key={worker.id}>
                        <td>
                          <div className="worker-cell">
                            <span className="worker-cell__title">{worker.id}</span>
                            <span className="text-subtle">
                              {worker.hostname ?? t("admin.workersPage.values.unknownHost")} /{" "}
                              {worker.version ?? t("admin.workersPage.values.unknownVersion")}
                            </span>
                            <span className="text-subtle">
                              {worker.tenant ?? t("admin.workersPage.values.defaultTenant")} /{" "}
                              {worker.instanceId ?? t("admin.workersPage.values.unknownInstance")}
                            </span>
                          </div>
                        </td>
                        <td>
                          <div className="worker-tag-list">
                            <span className={`badge ${worker.connected ? "badge--success" : "badge--muted"}`}>
                              {worker.connected
                                ? t("admin.workersPage.status.connected")
                                : t("admin.workersPage.status.offline")}
                            </span>
                            <span className={`badge ${worker.registered ? "badge--info" : "badge--muted"}`}>
                              {worker.registered
                                ? t("admin.workersPage.status.registered")
                                : t("admin.workersPage.status.unregistered")}
                            </span>
                            <span
                              className={`badge ${
                                heartbeat?.healthy ? "badge--success" : heartbeat ? "badge--warning" : "badge--muted"
                              }`}
                            >
                              {heartbeat?.healthy
                                ? t("admin.workersPage.status.healthy")
                                : heartbeat
                                  ? t("admin.workersPage.status.unhealthy")
                                  : t("admin.workersPage.status.unknown")}
                            </span>
                          </div>
                        </td>
                        <td>
                          <div className="worker-cell">
                            <span>{formatAge(worker.lastHeartbeatAt, t)}</span>
                            <span className="text-subtle">
                              {worker.lastHeartbeatAt ? new Date(worker.lastHeartbeatAt).toLocaleString() : "-"}
                            </span>
                          </div>
                        </td>
                        <td>
                          {worker.queues.length ? (
                            <div className="worker-tag-list">
                              {worker.queues.map((queue) => (
                                <span key={queue} className="chip">
                                  {queue}
                                </span>
                              ))}
                            </div>
                          ) : (
                            <span className="text-subtle">{t("admin.workersPage.messages.noQueues")}</span>
                          )}
                        </td>
                        <td>
                          {packages.chips.length ? (
                            <div className="worker-tag-list">
                              {packages.chips.map((pkg) => (
                                <span key={pkg} className="chip">
                                  {pkg}
                                </span>
                              ))}
                              {packages.extra > 0 && (
                                <span className="chip">+{packages.extra}</span>
                              )}
                            </div>
                          ) : (
                            <span className="text-subtle">{t("admin.workersPage.messages.noPackages")}</span>
                          )}
                        </td>
                        <td>
                          <div className="worker-metrics">
                            <span>{t("admin.workersPage.metrics.cpu")}: {formatPct(metrics?.cpuPct)}</span>
                            <span>{t("admin.workersPage.metrics.mem")}: {formatPct(metrics?.memPct)}</span>
                            <span>{t("admin.workersPage.metrics.disk")}: {formatPct(metrics?.diskPct)}</span>
                            <span>{t("admin.workersPage.metrics.inflight")}: {formatMetric(metrics?.inflight)}</span>
                            <span>{t("admin.workersPage.metrics.latency")}: {formatLatency(metrics?.latencyMs)}</span>
                          </div>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};

export default WorkersPage;
