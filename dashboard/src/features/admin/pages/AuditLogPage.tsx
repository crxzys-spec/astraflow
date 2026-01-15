import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import type { AuditEvent } from "../../../client/models";
import { useAuthStore } from "@store/authSlice";
import { listAuditEvents } from "../../../services/audit";
import { toApiError, type ApiError } from "../../../api/fetcher";

const AuditLogPage = () => {
  const isAdmin = useAuthStore((state) => state.hasRole(["admin"]));
  const { t } = useTranslation();
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
        <div className="card stack admin-panel">
          <h2>{t("admin.auditLogPage.accessDeniedTitle")}</h2>
          <p className="text-subtle">{t("admin.auditLogPage.accessDeniedMessage")}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="admin-view">
      <div className="card stack admin-panel">
        <header className="card__header admin-panel__header">
          <div>
            <span className="admin-panel__eyebrow">{t("admin.eyebrow")}</span>
            <h2>{t("admin.auditLogPage.title")}</h2>
            <p className="text-subtle admin-panel__description">{t("admin.auditLogPage.subtitle")}</p>
          </div>
          <button className="btn" type="button" onClick={() => { setCursor(undefined); void fetchAudit(true); }}>
            {t("common.refresh")}
          </button>
        </header>

        <form
          className="admin-section admin-section--filters stack"
          onSubmit={(evt) => {
            evt.preventDefault();
            setCursor(undefined);
            void fetchAudit(true);
          }}
        >
          <div className="builder-grid" style={{ gridTemplateColumns: "repeat(auto-fit,minmax(220px,1fr))" }}>
            <label className="stack">
              <span>{t("admin.auditLogPage.filters.action")}</span>
              <input
                type="text"
                value={filters.action}
                onChange={(evt) => setFilters((prev) => ({ ...prev, action: evt.target.value }))}
              />
            </label>
            <label className="stack">
              <span>{t("admin.auditLogPage.filters.actorId")}</span>
              <input
                type="text"
                value={filters.actorId}
                onChange={(evt) => setFilters((prev) => ({ ...prev, actorId: evt.target.value }))}
              />
            </label>
            <label className="stack">
              <span>{t("admin.auditLogPage.filters.targetType")}</span>
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
              {t("admin.auditLogPage.filters.clear")}
            </button>
            <button className="btn btn--primary" type="submit">
              {t("admin.auditLogPage.filters.apply")}
            </button>
          </div>
        </form>

        {isError && (
          <div className="admin-section admin-section--notice stack">
            <p className="error">
              {t("admin.auditLogPage.messages.loadError", { message: error?.message ?? t("common.unknownError") })}
            </p>
            <button className="btn" type="button" onClick={() => { setCursor(undefined); void fetchAudit(true); }}>
              {t("common.retry")}
            </button>
          </div>
        )}

        {isLoading ? (
          <div className="admin-section admin-section--table">
            <p className="text-subtle">{t("admin.auditLogPage.messages.loading")}</p>
          </div>
        ) : rows.length === 0 ? (
          <div className="admin-section admin-section--table">
            <p className="text-subtle">
              {hasFilters
                ? t("admin.auditLogPage.messages.emptyFiltered")
                : t("admin.auditLogPage.messages.empty")}
            </p>
          </div>
        ) : (
          <div className="admin-section admin-section--table stack">
            <div className="admin-table-wrap">
              <table className="data-table admin-table">
                <thead>
                  <tr>
                    <th>{t("admin.auditLogPage.table.time")}</th>
                    <th>{t("admin.auditLogPage.table.action")}</th>
                    <th>{t("admin.auditLogPage.table.actor")}</th>
                    <th>{t("admin.auditLogPage.table.target")}</th>
                    <th>{t("admin.auditLogPage.table.metadata")}</th>
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
            </div>
            {nextCursor && (
              <div className="builder-actions">
                <button
                  className="btn"
                  type="button"
                  onClick={() => setCursor(nextCursor)}
                  disabled={isLoading}
                >
                  {isLoading ? t("admin.auditLogPage.messages.loadingMore") : t("admin.auditLogPage.messages.loadMore")}
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
