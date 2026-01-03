import { useMemo, useState } from "react";
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

const formatAge = (iso?: string | null) => {
  if (!iso) {
    return "-";
  }
  const timestamp = Date.parse(iso);
  if (Number.isNaN(timestamp)) {
    return "-";
  }
  const diffMs = Date.now() - timestamp;
  if (diffMs < 0) {
    return "just now";
  }
  const seconds = Math.floor(diffMs / 1000);
  if (seconds < 60) {
    return `${seconds}s ago`;
  }
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) {
    return `${minutes}m ago`;
  }
  const hours = Math.floor(minutes / 60);
  if (hours < 24) {
    return `${hours}h ago`;
  }
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
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
          <h2>Worker Fleet</h2>
          <p className="text-subtle">Only administrators can view connected workers.</p>
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
            <span className="admin-panel__eyebrow">Administration</span>
            <h2>Worker Fleet</h2>
            <p className="text-subtle admin-panel__description">
              Inspect connection health, queues, and installed packages.
            </p>
          </div>
          <div className="builder-actions builder-actions--buttons">
            <button className="btn btn--ghost" type="button" onClick={clearFilters}>
              Clear Filters
            </button>
            <button className="btn" type="button" onClick={() => void refetch()} disabled={status === "loading"}>
              {status === "loading" ? "Refreshing..." : "Refresh"}
            </button>
          </div>
        </header>

        <div className="admin-section admin-section--stats worker-stats">
          <div className="worker-stat">
            <span className="worker-stat__label">Total</span>
            <span className="worker-stat__value">{stats.total}</span>
          </div>
          <div className="worker-stat">
            <span className="worker-stat__label">Connected</span>
            <span className="worker-stat__value">{stats.connected}</span>
          </div>
          <div className="worker-stat">
            <span className="worker-stat__label">Registered</span>
            <span className="worker-stat__value">{stats.registered}</span>
          </div>
          <div className="worker-stat">
            <span className="worker-stat__label">Healthy</span>
            <span className="worker-stat__value">{stats.healthy}</span>
          </div>
        </div>

        <form className="admin-section admin-section--filters">
          <div className="builder-grid" style={{ gridTemplateColumns: "repeat(auto-fit,minmax(220px,1fr))" }}>
            <label className="stack">
              <span>Search</span>
              <input
                type="text"
                value={filters.search}
                onChange={(evt) => setFilters((prev) => ({ ...prev, search: evt.target.value }))}
                placeholder="worker name, host, tenant"
              />
            </label>
            <label className="stack">
              <span>Queue</span>
              <input
                type="text"
                value={filters.queue}
                onChange={(evt) => setFilters((prev) => ({ ...prev, queue: evt.target.value }))}
                placeholder="default"
              />
            </label>
            <label className="stack">
              <span>Connection</span>
              <select
                value={filters.connection}
                onChange={(evt) => setFilters((prev) => ({ ...prev, connection: evt.target.value as FilterState["connection"] }))}
              >
                <option value="all">All</option>
                <option value="connected">Connected</option>
                <option value="disconnected">Disconnected</option>
              </select>
            </label>
            <label className="stack">
              <span>Health</span>
              <select
                value={filters.health}
                onChange={(evt) => setFilters((prev) => ({ ...prev, health: evt.target.value as FilterState["health"] }))}
              >
                <option value="all">All</option>
                <option value="healthy">Healthy</option>
                <option value="unhealthy">Unhealthy or unknown</option>
              </select>
            </label>
            <label className="stack">
              <span>Package</span>
              <input
                type="text"
                value={filters.packageName}
                onChange={(evt) => setFilters((prev) => ({ ...prev, packageName: evt.target.value }))}
                placeholder="package name"
              />
            </label>
            <label className="stack">
              <span>Package Status</span>
              <select
                value={filters.packageStatus}
                onChange={(evt) =>
                  setFilters((prev) => ({ ...prev, packageStatus: evt.target.value as FilterState["packageStatus"] }))
                }
              >
                <option value="all">All</option>
                <option value="installed">Installed</option>
                <option value="installing">Installing</option>
                <option value="uninstalling">Uninstalling</option>
                <option value="removed">Removed</option>
                <option value="failed">Failed</option>
                <option value="missing">Missing</option>
                <option value="unknown">Unknown</option>
              </select>
            </label>
          </div>
        </form>

        {status === "error" && (
          <div className="admin-section admin-section--notice stack">
            <p className="error">Unable to load workers: {error?.message ?? "Unknown error"}</p>
            <button className="btn" type="button" onClick={() => void refetch()}>
              Retry
            </button>
          </div>
        )}

        <div className="admin-section admin-section--table">
          <div className="admin-table-wrap">
            <table className="data-table worker-table admin-table">
              <thead>
                <tr>
                  <th>Worker</th>
                  <th>Status</th>
                  <th>Heartbeat</th>
                  <th>Queues</th>
                  <th>Packages</th>
                  <th>Metrics</th>
                </tr>
              </thead>
              <tbody>
                {status === "loading" ? (
                  <tr>
                    <td colSpan={6}>Loading workers...</td>
                  </tr>
                ) : visibleItems.length === 0 ? (
                  <tr>
                    <td colSpan={6}>No workers match the current filters.</td>
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
                              {worker.hostname ?? "unknown host"} / {worker.version ?? "unknown version"}
                            </span>
                            <span className="text-subtle">
                              {worker.tenant ?? "default"} / {worker.instanceId ?? "instance unknown"}
                            </span>
                          </div>
                        </td>
                        <td>
                          <div className="worker-tag-list">
                            <span className={`badge ${worker.connected ? "badge--success" : "badge--muted"}`}>
                              {worker.connected ? "Connected" : "Offline"}
                            </span>
                            <span className={`badge ${worker.registered ? "badge--info" : "badge--muted"}`}>
                              {worker.registered ? "Registered" : "Unregistered"}
                            </span>
                            <span
                              className={`badge ${
                                heartbeat?.healthy ? "badge--success" : heartbeat ? "badge--warning" : "badge--muted"
                              }`}
                            >
                              {heartbeat?.healthy ? "Healthy" : heartbeat ? "Unhealthy" : "Unknown"}
                            </span>
                          </div>
                        </td>
                        <td>
                          <div className="worker-cell">
                            <span>{formatAge(worker.lastHeartbeatAt)}</span>
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
                            <span className="text-subtle">No queues</span>
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
                            <span className="text-subtle">No packages</span>
                          )}
                        </td>
                        <td>
                          <div className="worker-metrics">
                            <span>CPU: {formatPct(metrics?.cpuPct)}</span>
                            <span>Mem: {formatPct(metrics?.memPct)}</span>
                            <span>Disk: {formatPct(metrics?.diskPct)}</span>
                            <span>Inflight: {formatMetric(metrics?.inflight)}</span>
                            <span>Latency: {formatLatency(metrics?.latencyMs)}</span>
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
