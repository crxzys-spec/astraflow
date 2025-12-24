import { Fragment, useCallback, useEffect, useMemo, useRef, useState, type ChangeEvent } from "react";
import { accountGateway } from "../../../services/account";
import { resourcesGateway } from "../../../services/resources";
import { useAuthStore } from "@store/authSlice";
import type { Resource, UserSummary } from "../../../client/models";
import "../account.css";

const formatResourceSize = (size?: number | null): string => {
  if (size == null) {
    return "-";
  }
  return `${size.toLocaleString()} bytes`;
};

const formatBytes = (value?: number) => {
  if (!value && value !== 0) {
    return "";
  }
  const units = ["B", "KB", "MB", "GB", "TB"];
  let size = value;
  let index = 0;
  while (size >= 1024 && index < units.length - 1) {
    size /= 1024;
    index += 1;
  }
  return `${size.toFixed(index === 0 ? 0 : 1)} ${units[index]}`;
};

const formatDate = (value?: string | Date | null): string => {
  if (!value) {
    return "-";
  }
  const date = typeof value === "string" ? new Date(value) : value;
  if (Number.isNaN(date.getTime())) {
    return "-";
  }
  return date.toLocaleString();
};

type UploadEntry = {
  key: string;
  name: string;
  size: number;
  progress: number;
  status: "queued" | "uploading" | "error";
  error?: string;
};

type PreviewKind = "image" | "video" | "audio";

type PreviewEntry = {
  status: "loading" | "ready" | "error";
  kind: PreviewKind;
  url?: string;
  error?: string;
};

type AccountSection = "profile" | "resources";

type AccountPageVariant = "full" | "profile" | "resources";

type AccountPageProps = {
  variant?: AccountPageVariant;
};

const isAbortError = (value: unknown) => {
  const code = (value as { code?: string })?.code;
  const name = (value as { name?: string })?.name;
  const message = (value as { message?: string })?.message;
  return code === "ERR_CANCELED" || name === "CanceledError" || name === "AbortError" || message === "canceled";
};

const inferPreviewKind = (resource: Resource): PreviewKind | null => {
  const mime = resource.mimeType?.toLowerCase();
  if (mime) {
    if (mime.startsWith("image/")) {
      return "image";
    }
    if (mime.startsWith("video/")) {
      return "video";
    }
    if (mime.startsWith("audio/")) {
      return "audio";
    }
  }
  const name = resource.filename?.toLowerCase() ?? "";
  if (/\.(png|jpg|jpeg|gif|webp|svg)$/.test(name)) {
    return "image";
  }
  if (/\.(mp4|webm|ogg)$/.test(name)) {
    return "video";
  }
  if (/\.(mp3|wav|ogg|flac|m4a)$/.test(name)) {
    return "audio";
  }
  return null;
};

const AccountPage = ({ variant = "full" }: AccountPageProps) => {
  const user = useAuthStore((state) => state.user);
  const updateUser = useAuthStore((state) => state.updateUser);
  const [profile, setProfile] = useState<UserSummary | null>(user ?? null);
  const [displayName, setDisplayName] = useState(user?.displayName ?? "");
  const [profileStatus, setProfileStatus] = useState<{ type: "idle" | "error" | "success"; message?: string }>({
    type: "idle",
  });
  const [saving, setSaving] = useState(false);

  const [resources, setResources] = useState<Resource[]>([]);
  const [resourceLoading, setResourceLoading] = useState(false);
  const [resourceError, setResourceError] = useState<string | null>(null);
  const [resourceStatus, setResourceStatus] = useState<{
    type: "idle" | "error" | "success";
    message?: string;
  }>({ type: "idle" });
  const [resourceSearch, setResourceSearch] = useState("");
  const [providerFilter, setProviderFilter] = useState("all");
  const [typeFilter, setTypeFilter] = useState("all");
  const [uploadEntries, setUploadEntries] = useState<UploadEntry[]>([]);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadProvider, setUploadProvider] = useState("default");
  const [textResourceName, setTextResourceName] = useState("");
  const [textResourceContent, setTextResourceContent] = useState("");
  const [textResourceType, setTextResourceType] = useState("text/plain");
  const [previews, setPreviews] = useState<Record<string, PreviewEntry>>({});
  const previewControllersRef = useRef(new Map<string, AbortController>());
  const previewsRef = useRef(previews);
  const [activeSection, setActiveSection] = useState<AccountSection>("profile");
  const isFullView = variant === "full";
  const activeView: AccountSection =
    variant === "resources" ? "resources" : variant === "profile" ? "profile" : activeSection;
  const pageTitle =
    variant === "resources" ? "Resource Center" : variant === "profile" ? "Personal Panel" : "Account";
  const pageSubtitle =
    variant === "resources"
      ? "Upload, organize, and manage your resources."
      : variant === "profile"
        ? "Review your profile details and access roles."
        : "Manage your profile and personal resources.";

  useEffect(() => {
    if (user) {
      setProfile(user);
      setDisplayName(user.displayName);
    }
  }, [user]);

  const loadProfile = useCallback(async () => {
    setProfileStatus({ type: "idle" });
    try {
      const data = await accountGateway.getProfile();
      setProfile(data);
      setDisplayName(data.displayName);
      updateUser(data);
    } catch (error) {
      console.error("Failed to load profile", error);
      setProfileStatus({ type: "error", message: "Unable to load profile." });
    }
  }, [updateUser]);

  const loadResources = useCallback(
    async (searchValue?: string) => {
      setResourceLoading(true);
      setResourceError(null);
      setResourceStatus({ type: "idle" });
      try {
        const items = await resourcesGateway.listResources({
          ownerId: "me",
          search: searchValue && searchValue.trim() ? searchValue.trim() : undefined,
        });
        setResources(items);
      } catch (error) {
        console.error("Failed to load resources", error);
        setResourceError("Unable to load resources.");
      } finally {
        setResourceLoading(false);
      }
    },
    []
  );

  useEffect(() => {
    if (variant !== "resources") {
      loadProfile();
    }
    if (variant !== "profile") {
      loadResources();
    }
  }, [loadProfile, loadResources, variant]);

  useEffect(() => {
    previewsRef.current = previews;
  }, [previews]);

  useEffect(() => {
    const resourceIds = new Set(resources.map((item) => item.resourceId));
    setPreviews((prev) => {
      let changed = false;
      const next = { ...prev };
      Object.keys(next).forEach((resourceId) => {
        if (!resourceIds.has(resourceId)) {
          changed = true;
          if (next[resourceId]?.url) {
            URL.revokeObjectURL(next[resourceId].url ?? "");
          }
          const controller = previewControllersRef.current.get(resourceId);
          if (controller) {
            controller.abort();
            previewControllersRef.current.delete(resourceId);
          }
          delete next[resourceId];
        }
      });
      return changed ? next : prev;
    });
  }, [resources]);

  useEffect(() => {
    return () => {
      Object.values(previewsRef.current).forEach((entry) => {
        if (entry.url) {
          URL.revokeObjectURL(entry.url);
        }
      });
      previewControllersRef.current.forEach((controller) => controller.abort());
      previewControllersRef.current.clear();
    };
  }, []);

  const handleSaveProfile = async () => {
    if (!profile) {
      return;
    }
    const nextName = displayName.trim();
    if (!nextName) {
      setProfileStatus({ type: "error", message: "Display name is required." });
      return;
    }
    setSaving(true);
    setProfileStatus({ type: "idle" });
    try {
      const updated = await accountGateway.updateProfile({ displayName: nextName });
      setProfile(updated);
      setDisplayName(updated.displayName);
      updateUser(updated);
      setProfileStatus({ type: "success", message: "Profile updated." });
    } catch (error) {
      console.error("Failed to update profile", error);
      setProfileStatus({ type: "error", message: "Unable to update profile." });
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteResource = async (resourceId: string) => {
    if (!window.confirm("Delete this resource?")) {
      return;
    }
    try {
      await resourcesGateway.delete(resourceId);
      setResources((prev) => prev.filter((item) => item.resourceId !== resourceId));
    } catch (error) {
      console.error("Failed to delete resource", error);
      setResourceError("Unable to delete resource.");
    }
  };

  const handleRevokeGrants = async (resource: Resource) => {
    setResourceError(null);
    setResourceStatus({ type: "idle" });
    try {
      const grants = await resourcesGateway.listGrants({ resourceId: resource.resourceId });
      if (!grants.length) {
        setResourceStatus({ type: "success", message: "No grants to revoke for this resource." });
        return;
      }
      const confirmed = window.confirm(
        `Revoke ${grants.length} grant(s) for "${resource.filename || resource.resourceId}"?`,
      );
      if (!confirmed) {
        return;
      }
      await Promise.all(grants.map((grant) => resourcesGateway.deleteGrant(grant.grantId)));
      setResourceStatus({ type: "success", message: "Grants revoked." });
    } catch (error) {
      console.error("Failed to revoke grants", error);
      setResourceStatus({ type: "error", message: "Unable to revoke grants." });
    }
  };

  const updateUploadEntry = (key: string, patch: Partial<UploadEntry>) => {
    setUploadEntries((prev) => prev.map((entry) => (entry.key === key ? { ...entry, ...patch } : entry)));
  };

  const removeUploadEntry = (key: string) => {
    setUploadEntries((prev) => prev.filter((entry) => entry.key !== key));
  };

  const addUploadEntries = (entries: UploadEntry[]) => {
    if (!entries.length) {
      return;
    }
    setUploadEntries((prev) => [...prev, ...entries]);
  };

  const handleUploadFiles = useCallback(
    async (files: File[]) => {
      if (!files.length || uploading) {
        return false;
      }
      setUploadError(null);
      const batchId = Date.now();
      const queue = files.map((file, index) => ({
        file,
        key: `${file.name}-${file.size}-${file.lastModified}-${batchId}-${index}`,
      }));
      addUploadEntries(
        queue.map(({ file, key }) => ({
          key,
          name: file.name,
          size: file.size,
          progress: 0,
          status: "queued",
        })),
      );
      setUploading(true);
      const provider = uploadProvider === "default" ? undefined : uploadProvider;
      let uploadedAny = false;
      for (const { file, key } of queue) {
        updateUploadEntry(key, { status: "uploading" });
        try {
          const resource = await resourcesGateway.upload(file, {
            provider,
            onProgress: (progress) => updateUploadEntry(key, { progress }),
          });
          removeUploadEntry(key);
          if (resource) {
            uploadedAny = true;
          }
        } catch (error) {
          const message = (error as { message?: string })?.message ?? "Upload failed.";
          updateUploadEntry(key, { status: "error", error: message });
          setUploadError(message);
        }
      }
      setUploading(false);
      if (uploadedAny) {
        await loadResources(resourceSearch);
      }
      return uploadedAny;
    },
    [loadResources, resourceSearch, uploadProvider, uploading],
  );

  const handleUploadInput = (event: ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files ? Array.from(event.target.files) : [];
    void handleUploadFiles(files);
    event.target.value = "";
  };

  const resolveTextFilename = (rawName: string, mimeType: string) => {
    const trimmed = rawName.trim().replace(/\.+$/, "");
    const base = trimmed || "untitled";
    const hasExtension = /\.[A-Za-z0-9]+$/.test(base);
    if (hasExtension) {
      return base;
    }
    const extension =
      mimeType === "application/json" ? ".json" : mimeType === "text/markdown" ? ".md" : ".txt";
    return `${base}${extension}`;
  };

  const handleCreateTextResource = async () => {
    if (!textResourceContent.trim()) {
      setUploadError("Text content is empty.");
      return;
    }
    const filename = resolveTextFilename(textResourceName, textResourceType);
    const file = new File([textResourceContent], filename, {
      type: textResourceType,
    });
    const uploaded = await handleUploadFiles([file]);
    if (uploaded) {
      setTextResourceContent("");
    }
  };

  const handleDismissUpload = (key: string) => {
    removeUploadEntry(key);
  };

  const setPreviewEntry = (resourceId: string, entry: PreviewEntry) => {
    setPreviews((prev) => ({ ...prev, [resourceId]: entry }));
  };

  const clearPreviewEntry = (resourceId: string) => {
    setPreviews((prev) => {
      const existing = prev[resourceId];
      if (existing?.url) {
        URL.revokeObjectURL(existing.url);
      }
      const next = { ...prev };
      delete next[resourceId];
      return next;
    });
    const controller = previewControllersRef.current.get(resourceId);
    if (controller) {
      controller.abort();
      previewControllersRef.current.delete(resourceId);
    }
  };

  const handleTogglePreview = async (resource: Resource) => {
    const kind = inferPreviewKind(resource);
    if (!kind) {
      return;
    }
    const resourceId = resource.resourceId;
    if (previews[resourceId]) {
      clearPreviewEntry(resourceId);
      return;
    }
    const controller = new AbortController();
    previewControllersRef.current.set(resourceId, controller);
    setPreviewEntry(resourceId, { status: "loading", kind });
    try {
      const { blob } = await resourcesGateway.fetchBlob(resourceId, {
        signal: controller.signal,
        timeoutMs: 120_000,
      });
      const url = URL.createObjectURL(blob);
      setPreviewEntry(resourceId, { status: "ready", kind, url });
    } catch (error) {
      if (isAbortError(error)) {
        return;
      }
      const message = (error as { message?: string })?.message ?? "Failed to load preview.";
      setPreviewEntry(resourceId, { status: "error", kind, error: message });
    } finally {
      previewControllersRef.current.delete(resourceId);
    }
  };

  const providerOptions = useMemo(() => {
    const values = new Set(resources.map((item) => item.provider).filter(Boolean));
    return ["all", ...Array.from(values).sort()];
  }, [resources]);

  const uploadProviderOptions = useMemo(() => {
    const values = new Set(resources.map((item) => item.provider).filter(Boolean));
    values.add("local");
    values.add("db");
    return Array.from(values).sort();
  }, [resources]);

  const textResourceSize = useMemo(() => new Blob([textResourceContent]).size, [textResourceContent]);

  const typeOptions = useMemo(() => {
    const values = new Set(resources.map((item) => item.type).filter(Boolean));
    return ["all", ...Array.from(values).sort()];
  }, [resources]);

  const filteredResources = useMemo(() => {
    return resources.filter((resource) => {
      if (providerFilter !== "all" && resource.provider !== providerFilter) {
        return false;
      }
      if (typeFilter !== "all" && resource.type !== typeFilter) {
        return false;
      }
      return true;
    });
  }, [resources, providerFilter, typeFilter]);

  const hasProfileChanges = Boolean(profile && displayName.trim() && displayName.trim() !== profile.displayName);

  return (
    <div className="account-page">
      <div className="account-header">
        <h2>{pageTitle}</h2>
        <p className="text-subtle">{pageSubtitle}</p>
      </div>

      <div className={`account-layout${isFullView ? "" : " account-layout--single"}`}>
        {isFullView && (
          <aside className="account-sidebar">
            <nav className="account-menu">
              <button
                type="button"
                className={`account-menu__button${activeSection === "profile" ? " is-active" : ""}`}
                onClick={() => setActiveSection("profile")}
              >
                Personal Panel
              </button>
              <button
                type="button"
                className={`account-menu__button${activeSection === "resources" ? " is-active" : ""}`}
                onClick={() => setActiveSection("resources")}
              >
                Resource Center
              </button>
            </nav>
          </aside>
        )}

        <section className="account-content">
          {activeView === "profile" && (
            <div className="card">
              <header className="card__header">
                <h3>Profile</h3>
              </header>
              {profile ? (
                <div className="stack">
                  <div className="account-field">
                    <span className="account-field__label">Display name</span>
                    <input
                      type="text"
                      value={displayName}
                      onChange={(event) => setDisplayName(event.target.value)}
                    />
                  </div>
                  <div className="account-field">
                    <span className="account-field__label">Username</span>
                    <div className="account__mono">{profile.username}</div>
                  </div>
                  <div className="account-field">
                    <span className="account-field__label">User id</span>
                    <div className="account__mono">{profile.userId}</div>
                  </div>
                  <div className="account-field">
                    <span className="account-field__label">Roles</span>
                    <div className="account-inline">
                      {profile.roles.map((role) => (
                        <span key={role} className="account-pill account-pill--muted">
                          {role}
                        </span>
                      ))}
                    </div>
                  </div>
                  <div className="account-field">
                    <span className="account-field__label">Status</span>
                    <div className={`account-status ${profile.isActive ? "" : "account-status--error"}`}>
                      {profile.isActive ? "Active" : "Disabled"}
                    </div>
                  </div>
                  <div className="account-actions">
                    <button
                      type="button"
                      className="btn btn--primary"
                      onClick={handleSaveProfile}
                      disabled={saving || !hasProfileChanges}
                    >
                      {saving ? "Saving..." : "Save changes"}
                    </button>
                    <button type="button" className="btn btn--ghost" onClick={loadProfile}>
                      Refresh
                    </button>
                  </div>
                  {profileStatus.type !== "idle" && (
                    <div
                      className={`account-note ${
                        profileStatus.type === "error" ? "account-status--error" : "account-status--success"
                      }`}
                    >
                      {profileStatus.message}
                    </div>
                  )}
                </div>
              ) : (
                <p className="text-subtle">No profile loaded.</p>
              )}
            </div>
          )}

          {activeView === "resources" && (
            <div className="card">
              <header className="card__header">
                <h3>Resource Library</h3>
              </header>
              <div className="stack">
                <div className="account-resource-upload">
                  <div className="account-upload-card">
                    <label className="account-upload-dropzone">
                      <input
                        className="account-upload-input"
                        type="file"
                        multiple
                        onChange={handleUploadInput}
                        disabled={uploading}
                      />
                      <span className="account-upload-title">Upload files</span>
                      <span className="account-upload-subtitle">Drag &amp; drop or click to browse.</span>
                    </label>
                    <div className="account-upload-options">
                      <label className="account-field account-resource-upload__field">
                        <span className="account-field__label">Provider</span>
                        <select
                          value={uploadProvider}
                          onChange={(event) => setUploadProvider(event.target.value)}
                          disabled={uploading}
                        >
                          <option value="default">Default provider</option>
                          {uploadProviderOptions.map((provider) => (
                            <option key={provider} value={provider}>
                              {provider}
                            </option>
                          ))}
                        </select>
                      </label>
                      {uploading && <span className="account-upload-status">Uploading...</span>}
                    </div>
                  </div>
                  <div className="account-text-resource">
                    <div className="account-text-resource__header">
                      <div>
                        <h4>Quick text resource</h4>
                        <p className="text-subtle">Store prompts, notes, or config snippets without uploading files.</p>
                      </div>
                      <span className="account-text-resource__size">{formatBytes(textResourceSize)}</span>
                    </div>
                    <div className="account-text-resource__grid">
                      <label className="account-field">
                        <span className="account-field__label">Name</span>
                        <input
                          type="text"
                          value={textResourceName}
                          onChange={(event) => setTextResourceName(event.target.value)}
                          placeholder="untitled.txt"
                          disabled={uploading}
                        />
                      </label>
                      <label className="account-field account-text-resource__content">
                        <span className="account-field__label">Content</span>
                        <textarea
                          rows={6}
                          value={textResourceContent}
                          onChange={(event) => setTextResourceContent(event.target.value)}
                          placeholder="Paste or type your text here."
                          disabled={uploading}
                        />
                      </label>
                    </div>
                    <div className="account-text-resource__actions">
                      <label className="account-field">
                        <span className="account-field__label">Content type</span>
                        <select
                          value={textResourceType}
                          onChange={(event) => setTextResourceType(event.target.value)}
                          disabled={uploading}
                        >
                          <option value="text/plain">Plain text (.txt)</option>
                          <option value="text/markdown">Markdown (.md)</option>
                          <option value="application/json">JSON (.json)</option>
                        </select>
                      </label>
                      <button
                        type="button"
                        className="btn btn--primary"
                        onClick={handleCreateTextResource}
                        disabled={uploading || !textResourceContent.trim()}
                      >
                        Create resource
                      </button>
                    </div>
                    <p className="account-text-resource__hint">Uses the provider selected above.</p>
                  </div>
                  {uploadError && <p className="error">{uploadError}</p>}
                  {uploadEntries.length > 0 && (
                    <ul className="account-upload-list">
                      {uploadEntries.map((entry) => {
                        const progressPct = Math.round(Math.min(100, Math.max(0, entry.progress * 100)));
                        const statusLabel =
                          entry.status === "error"
                            ? "Failed"
                            : entry.status === "queued"
                              ? "Queued"
                              : `${progressPct}%`;
                        return (
                          <li key={entry.key} className="account-upload-item">
                            <div className="account-upload-row">
                              <span className="account-upload-name">{entry.name}</span>
                              <span className="account-upload-meta">{formatBytes(entry.size)}</span>
                              <span className="account-upload-progress-text">{statusLabel}</span>
                              {entry.status === "error" && (
                                <button
                                  type="button"
                                  className="btn btn--ghost"
                                  onClick={() => handleDismissUpload(entry.key)}
                                >
                                  Remove
                                </button>
                              )}
                            </div>
                            <div className="account-upload-bar">
                              <div className="account-upload-progress" style={{ width: `${progressPct}%` }} />
                            </div>
                            {entry.error && <div className="account-upload-error">{entry.error}</div>}
                          </li>
                        );
                      })}
                    </ul>
                  )}
                </div>

                <div className="account-resource-toolbar">
                  <div className="account-resource-filters">
                    <label className="account-field">
                      <span className="account-field__label">Search</span>
                      <input
                        type="text"
                        placeholder="filename or id"
                        value={resourceSearch}
                        onChange={(event) => setResourceSearch(event.target.value)}
                      />
                    </label>
                    <label className="account-field">
                      <span className="account-field__label">Provider</span>
                      <select value={providerFilter} onChange={(event) => setProviderFilter(event.target.value)}>
                        {providerOptions.map((provider) => (
                          <option key={provider} value={provider}>
                            {provider === "all" ? "All providers" : provider}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label className="account-field">
                      <span className="account-field__label">Type</span>
                      <select value={typeFilter} onChange={(event) => setTypeFilter(event.target.value)}>
                        {typeOptions.map((type) => (
                          <option key={type} value={type}>
                            {type === "all" ? "All types" : type}
                          </option>
                        ))}
                      </select>
                    </label>
                  </div>
                  <div className="account-actions">
                    <button
                      type="button"
                      className="btn btn--ghost"
                      onClick={() => loadResources(resourceSearch)}
                      disabled={resourceLoading}
                    >
                      {resourceLoading ? "Refreshing..." : "Refresh"}
                    </button>
                  </div>
                </div>

                {resourceError && <p className="error">{resourceError}</p>}
                {resourceStatus.type !== "idle" && (
                  <p
                    className={`account-note ${
                      resourceStatus.type === "error" ? "account-status--error" : "account-status--success"
                    }`}
                  >
                    {resourceStatus.message}
                  </p>
                )}
                {resourceLoading && <p className="text-subtle">Loading resources...</p>}
                {!resourceLoading && filteredResources.length === 0 && (
                  <p className="text-subtle">No resources found.</p>
                )}
                {!resourceLoading && filteredResources.length > 0 && (
                  <table className="data-table account-resource-table">
                    <thead>
                      <tr>
                        <th>File</th>
                        <th>Resource Id</th>
                        <th>Provider</th>
                        <th>Type</th>
                        <th>Size</th>
                        <th>Created</th>
                        <th>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredResources.map((resource) => {
                        const previewKind = inferPreviewKind(resource);
                        const preview = previews[resource.resourceId];
                        return (
                          <Fragment key={resource.resourceId}>
                            <tr>
                              <td>{resource.filename || resource.resourceId}</td>
                              <td className="account__mono">{resource.resourceId}</td>
                              <td>
                                <span className="account-pill">{resource.provider}</span>
                              </td>
                              <td>{resource.type}</td>
                              <td>{formatResourceSize(resource.sizeBytes)}</td>
                              <td>{formatDate(resource.createdAt)}</td>
                              <td>
                                <div className="account-resource-actions">
                                  {previewKind && (
                                    <button
                                      type="button"
                                      className={`btn btn--ghost account-resource-preview-toggle${
                                        preview ? " is-active" : ""
                                      }`}
                                      onClick={() => handleTogglePreview(resource)}
                                    >
                                      {preview?.status === "loading" ? "Loading" : preview ? "Hide" : "Preview"}
                                    </button>
                                  )}
                                  <button
                                    type="button"
                                    className="btn btn--ghost"
                                    onClick={() =>
                                      resourcesGateway.download(resource.resourceId, resource.filename ?? undefined)
                                    }
                                  >
                                    Download
                                  </button>
                                  <button
                                    type="button"
                                    className="btn btn--ghost"
                                    onClick={() => handleDeleteResource(resource.resourceId)}
                                  >
                                    Delete
                                  </button>
                                  <button
                                    type="button"
                                    className="btn btn--ghost"
                                    onClick={() => handleRevokeGrants(resource)}
                                  >
                                    Revoke grants
                                  </button>
                                </div>
                              </td>
                            </tr>
                            {preview && (
                              <tr className="account-resource-preview-row">
                                <td colSpan={7}>
                                  <div className="account-resource-preview">
                                    {preview.status === "loading" && <span>Loading preview...</span>}
                                    {preview.status === "error" && (
                                      <span className="account-resource-preview__error">{preview.error}</span>
                                    )}
                                    {preview.status === "ready" && preview.url && preview.kind === "image" && (
                                      <img src={preview.url} alt={resource.filename ?? "preview"} />
                                    )}
                                    {preview.status === "ready" && preview.url && preview.kind === "video" && (
                                      <video src={preview.url} controls preload="metadata" />
                                    )}
                                    {preview.status === "ready" && preview.url && preview.kind === "audio" && (
                                      <audio src={preview.url} controls preload="metadata" />
                                    )}
                                  </div>
                                </td>
                              </tr>
                            )}
                          </Fragment>
                        );
                      })}
                    </tbody>
                  </table>
                )}
              </div>
            </div>
          )}
        </section>
      </div>
    </div>
  );
};

export default AccountPage;
