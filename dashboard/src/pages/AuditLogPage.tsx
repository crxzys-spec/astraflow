import { useEffect, useMemo, useState } from "react";
import type { AuditEvent } from "../client/models";
import { useAuthStore } from "../features/auth/store";
import { listAuditEvents } from "../services/audit";
import { toApiError, type ApiError } from "../api/fetcher";

const AuditLogPage = () => {
  const isAdmin = useAuthStore((state) => state.hasRole(["admin"]));
  const [filters, setFilters] = useState({ action: "", actorId: "", targetType: "" });
  const [cursor, setCursor] = useState<string | undefined>(undefined);
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [error, setError] = useState<ApiError | null>(null);

  const queryParams = {
    action: filters.action || undefined,
    actorId: filters.actorId || undefined,
    targetType: filters.targetType || undefined,
    cursor,
  };

  const [nextCursor, setNextCursor] = useState<string | null>(null);

  const fetchAudit = async (reset: boolean) => {
    if (!isAdmin) {
      return;
    }
    const nextCursorValue = reset ? undefined : cursor;
    setStatus("loading");
    setError(null);
    try {
      const response = await listAuditEvents({ ...queryParams, cursor: nextCursorValue });
      setNextCursor(response?.nextCursor ?? null);
      setEvents((prev) => (reset ? response.items ?? [] : [...prev, ...(response.items ?? [])]));
      setStatus("success");
    } catch (err) {
      setError(toApiError(err));
      setStatus("error");
    }
  };

  useEffect(() => {
    if (!isAdmin) {
      setEvents([]);
      setCursor(undefined);
      setStatus("idle");
      setError(null);
    }
  }, [isAdmin]);

  useEffect(() => {
    void fetchAudit(true);
  }, [filters.action, filters.actorId, filters.targetType, isAdmin]);

  useEffect(() => {
    if (!isAdmin) {
      return;
    }
    if (cursor) {
      void fetchAudit(false);
    }
  }, [cursor, isAdmin]);

  const rows = useMemo(() => events, [events]);
  const hasFilters =
    Boolean(filters.action.trim()) || Boolean(filters.actorId.trim()) || Boolean(filters.targetType.trim());

  const isLoading = status === "loading";
  const isError = status === "error";

  if (!isAdmin) {
    return (
      <div className="admin-view">
        <div className="card stack">
          <h2>Audit Events</h2>
          <p className="text-subtle">
            Only administrators can view the audit trail. Contact your AstraFlow admin to request access.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="admin-view">
      <div className="card stack">
      <header className="card__header">
        <div>
          <h2>Audit Events</h2>
          <p className="text-subtle">Latest privileged operations captured by the scheduler.</p>
        </div>
        <button className="btn" type="button" onClick={() => { setCursor(undefined); void fetchAudit(true); }}>
          Refresh
        </button>
      </header>

      <form
        className="card card--surface stack"
        onSubmit={(evt) => {
          evt.preventDefault();
          setCursor(undefined);
          void fetchAudit(true);
        }}
      >
        <div className="builder-grid" style={{ gridTemplateColumns: "repeat(auto-fit,minmax(220px,1fr))" }}>
          <label className="stack">
            <span>Action</span>
            <input
              type="text"
              value={filters.action}
              onChange={(evt) => setFilters((prev) => ({ ...prev, action: evt.target.value }))}
            />
          </label>
          <label className="stack">
            <span>Actor ID</span>
            <input
              type="text"
              value={filters.actorId}
              onChange={(evt) => setFilters((prev) => ({ ...prev, actorId: evt.target.value }))}
            />
          </label>
          <label className="stack">
            <span>Target Type</span>
            <input
              type="text"
              value={filters.targetType}
              onChange={(evt) => setFilters((prev) => ({ ...prev, targetType: evt.target.value }))}
            />
          </label>
        </div>
        <div className="builder-actions">
          <button
            className="btn btn--ghost"
            type="button"
            onClick={() => {
              setFilters({ action: "", actorId: "", targetType: "" });
              setCursor(undefined);
            }}
          >
            Clear
          </button>
          <button className="btn btn--primary" type="submit">
            Apply Filters
          </button>
        </div>
      </form>

      {isError && (
        <div className="card stack">
          <p className="error">Unable to load audit events: {error?.message ?? "Unknown error"}</p>
          <button className="btn" type="button" onClick={() => { setCursor(undefined); void fetchAudit(true); }}>
            Retry
          </button>
        </div>
      )}

      {isLoading ? (
        <p>Loading audit events...</p>
      ) : rows.length === 0 ? (
        <p>{hasFilters ? "No audit events match the selected filters." : "No audit events recorded yet."}</p>
      ) : (
        <div className="card card--surface stack">
          <table className="data-table">
            <thead>
              <tr>
                <th>Time</th>
                <th>Action</th>
                <th>Actor</th>
                <th>Target</th>
                <th>Metadata</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((event) => (
                <tr key={event.eventId}>
                  <td>{new Date(event.createdAt).toLocaleString()}</td>
                  <td>{event.action}</td>
                  <td>{event.actorId ?? "-"}</td>
                  <td>
                    {event.targetType}
                    {event.targetId ? ` / ${event.targetId}` : ""}
                  </td>
                  <td>
                    {event.metadata ? (
                      <pre className="audit-log__metadata">{JSON.stringify(event.metadata, null, 2)}</pre>
                    ) : (
                      "-"
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {nextCursor && (
            <div className="builder-actions">
              <button
                className="btn"
                type="button"
                onClick={() => setCursor(nextCursor)}
                disabled={isLoading}
              >
                {isLoading ? "Loading..." : "Load More"}
              </button>
            </div>
          )}
        </div>
      )}
      </div>
    </div>
  );
};

export default AuditLogPage;





