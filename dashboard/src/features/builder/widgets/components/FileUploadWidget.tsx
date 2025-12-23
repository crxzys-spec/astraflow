import { useEffect, useMemo, useRef, useState } from "react";
import type { ChangeEvent, DragEvent } from "react";
import type { WidgetRendererProps } from "../registry";
import type { Resource } from "../../../../client/models";
import { resourcesGateway } from "../../../../services/resources";
import { useMessageCenter } from "../../../../components/MessageCenter";

type WidgetOptions = {
  accept?: string;
  multiple?: boolean;
  maxBytes?: number;
  maxFiles?: number;
  maxParallel?: number;
  chunkParallel?: number;
  helperText?: string;
  deleteOnRemove?: boolean;
};

type UploadEntry = {
  key: string;
  name: string;
  size: number;
  progress: number;
  status: "queued" | "uploading" | "paused" | "error";
  error?: string;
};

type PreviewKind = "image" | "video" | "audio";

type PreviewEntry = {
  status: "loading" | "ready" | "error";
  kind: PreviewKind;
  url?: string;
  error?: string;
};

const isAbortError = (value: unknown) => {
  const code = (value as { code?: string })?.code;
  const name = (value as { name?: string })?.name;
  const message = (value as { message?: string })?.message;
  return code === "ERR_CANCELED" || name === "CanceledError" || name === "AbortError" || message === "canceled";
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

const isResource = (value: unknown): value is Resource =>
  Boolean(value && typeof value === "object" && "resourceId" in value);

const dedupeResources = (items: Resource[]): Resource[] => {
  const seen = new Set<string>();
  const deduped: Resource[] = [];
  for (const item of items) {
    const resourceId = item.resourceId;
    if (!resourceId || seen.has(resourceId)) {
      continue;
    }
    seen.add(resourceId);
    deduped.push(item);
  }
  return deduped;
};

const normalizeResources = (value: unknown): Resource[] => {
  if (Array.isArray(value)) {
    return dedupeResources(value.filter(isResource));
  }
  if (isResource(value)) {
    return [value];
  }
  return [];
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



export const FileUploadWidget = ({ widget, value, onChange, readOnly }: WidgetRendererProps) => {
  const options = (widget.options ?? {}) as WidgetOptions;
  const accept = typeof options.accept === "string" ? options.accept : undefined;
  const maxBytes = typeof options.maxBytes === "number" ? options.maxBytes : undefined;
  const maxFiles = typeof options.maxFiles === "number" ? options.maxFiles : undefined;
  const allowMultiple = Boolean(options.multiple || (maxFiles && maxFiles > 1));
  const maxParallelRaw = typeof options.maxParallel === "number" ? options.maxParallel : 2;
  const maxParallel = Math.max(1, Math.floor(maxParallelRaw));
  const chunkParallelRaw = typeof options.chunkParallel === "number" ? options.chunkParallel : undefined;
  const chunkParallel = chunkParallelRaw ? Math.max(1, Math.floor(chunkParallelRaw)) : undefined;
  const helperText = typeof options.helperText === "string" ? options.helperText : undefined;
  const deleteOnRemove = Boolean(options.deleteOnRemove);
  const { pushMessage } = useMessageCenter();

  const resources = useMemo(() => normalizeResources(value), [value]);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [uploads, setUploads] = useState<UploadEntry[]>([]);
  const [previews, setPreviews] = useState<Record<string, PreviewEntry>>({});
  const [isDragging, setIsDragging] = useState(false);
  const dragCounter = useRef(0);
  const uploadFilesRef = useRef(new Map<string, File>());
  const uploadControllersRef = useRef(new Map<string, AbortController>());
  const abortReasonsRef = useRef(new Map<string, "paused" | "cancelled">());
  const previewControllersRef = useRef(new Map<string, AbortController>());
  const previewsRef = useRef(previews);
  const activeUploadsRef = useRef(0);

  const applyChange = (next: Resource[]) => {
    if (allowMultiple) {
      onChange(dedupeResources(next));
      return;
    }
    onChange(next[0] ?? null);
  };

  const updateUploadEntry = (key: string, patch: Partial<UploadEntry>) => {
    setUploads((prev) => prev.map((entry) => (entry.key === key ? { ...entry, ...patch } : entry)));
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

  const removeUploadEntry = (key: string) => {
    setUploads((prev) => prev.filter((entry) => entry.key !== key));
  };

  const addUploadEntries = (entries: UploadEntry[]) => {
    if (!entries.length) {
      return;
    }
    setUploads((prev) => [...prev, ...entries]);
  };

  const updateActiveUploads = (delta: number) => {
    activeUploadsRef.current = Math.max(0, activeUploadsRef.current + delta);
    setIsUploading(activeUploadsRef.current > 0);
  };

  const startUpload = async (key: string, file: File): Promise<Resource | null> => {
    updateUploadEntry(key, { status: "uploading", error: undefined });
    const controller = new AbortController();
    uploadControllersRef.current.set(key, controller);
    updateActiveUploads(1);
    try {
      const resource = await resourcesGateway.upload(file, {
        onProgress: (progress) => updateUploadEntry(key, { progress }),
        signal: controller.signal,
        preserveSession: true,
        chunkConcurrency: chunkParallel,
      });
      removeUploadEntry(key);
      uploadFilesRef.current.delete(key);
      return resource;
    } catch (uploadError) {
      if (isAbortError(uploadError)) {
        const reason = abortReasonsRef.current.get(key);
        abortReasonsRef.current.delete(key);
        if (reason === "paused") {
          updateUploadEntry(key, { status: "paused", error: undefined });
          return null;
        }
        if (reason === "cancelled") {
          return null;
        }
      }
      const message = (uploadError as { message?: string })?.message ?? "Upload failed.";
      updateUploadEntry(key, { status: "error", error: message });
      setError(message);
      return null;
    } finally {
      uploadControllersRef.current.delete(key);
      updateActiveUploads(-1);
    }
  };

  const handlePauseUpload = (key: string) => {
    const controller = uploadControllersRef.current.get(key);
    if (controller) {
      abortReasonsRef.current.set(key, "paused");
      controller.abort();
    }
    updateUploadEntry(key, { status: "paused", error: undefined });
  };

  const handleCancelUpload = async (key: string) => {
    const controller = uploadControllersRef.current.get(key);
    const file = uploadFilesRef.current.get(key);
    if (controller) {
      abortReasonsRef.current.set(key, "cancelled");
      controller.abort();
    }
    uploadControllersRef.current.delete(key);
    uploadFilesRef.current.delete(key);
    removeUploadEntry(key);
    if (file) {
      await resourcesGateway.abortUpload(file);
    }
  };

  const handleDismissUpload = (key: string) => {
    void handleCancelUpload(key);
  };

  const handleRetryUpload = async (key: string) => {
    if (readOnly) {
      return;
    }
    const file = uploadFilesRef.current.get(key);
    if (!file) {
      removeUploadEntry(key);
      return;
    }
    const resource = await startUpload(key, file);
    if (resource) {
      const next = allowMultiple ? [...resources, resource] : [resource];
      applyChange(next);
    }
  };

  const handleFiles = async (files: File[]) => {
    if (readOnly || isUploading) {
      return;
    }
    setError(null);
    if (!files.length) {
      return;
    }
    if (!allowMultiple && files.length > 1) {
      setError("Only one file is allowed.");
      return;
    }
    if (maxFiles && resources.length + files.length > maxFiles) {
      setError(`No more than ${maxFiles} file(s) allowed.`);
      return;
    }
    const batchId = Date.now();
    const queue = files.map((file, index) => ({
      file,
      key: `${file.name}-${file.size}-${file.lastModified}-${batchId}-${index}`,
    }));
    queue.forEach(({ file, key }) => {
      uploadFilesRef.current.set(key, file);
    });
    addUploadEntries(
      queue.map(({ file, key }) => ({
        key,
        name: file.name,
        size: file.size,
        progress: 0,
        status: "queued",
      })),
    );
    const uploaded: Resource[] = [];
    const seenResourceIds = new Set(resources.map((item) => item.resourceId));
    let cursor = 0;
    const workerCount = Math.min(maxParallel, queue.length);
    const workers = Array.from({ length: workerCount }, async () => {
      while (cursor < queue.length) {
        const current = queue[cursor];
        cursor += 1;
        if (!current) {
          break;
        }
        const { file, key } = current;
        if (maxBytes && file.size > maxBytes) {
          const message = `"${file.name}" exceeds the size limit.`;
          updateUploadEntry(key, { status: "error", error: message, progress: 0 });
          setError(message);
          continue;
        }
        const resource = await startUpload(key, file);
        if (resource) {
          if (seenResourceIds.has(resource.resourceId)) {
            pushMessage({
              id: `upload-duplicate-${resource.resourceId}`,
              content: `Already attached "${resource.filename ?? resource.resourceId}". Skipped duplicate.`,
              tone: "info",
            });
            continue;
          }
          seenResourceIds.add(resource.resourceId);
          uploaded.push(resource);
        }
      }
    });
    await Promise.all(workers);
    if (uploaded.length > 0) {
      const next = allowMultiple ? [...resources, ...uploaded] : [uploaded[0]];
      applyChange(next);
    }
  };

  const handleUpload = (event: ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files ? Array.from(event.target.files) : [];
    void handleFiles(files);
    event.target.value = "";
  };

  const handleDragEnter = (event: DragEvent<HTMLLabelElement>) => {
    event.preventDefault();
    if (readOnly || isUploading) {
      return;
    }
    dragCounter.current += 1;
    setIsDragging(true);
  };

  const handleDragLeave = (event: DragEvent<HTMLLabelElement>) => {
    event.preventDefault();
    if (readOnly || isUploading) {
      return;
    }
    dragCounter.current = Math.max(0, dragCounter.current - 1);
    if (dragCounter.current === 0) {
      setIsDragging(false);
    }
  };

  const handleDrop = (event: DragEvent<HTMLLabelElement>) => {
    event.preventDefault();
    if (readOnly || isUploading) {
      return;
    }
    dragCounter.current = 0;
    setIsDragging(false);
    const files = Array.from(event.dataTransfer.files || []);
    void handleFiles(files);
  };

  const handleDragOver = (event: DragEvent<HTMLLabelElement>) => {
    event.preventDefault();
    if (readOnly || isUploading) {
      return;
    }
    event.dataTransfer.dropEffect = "copy";
  };

  const dropzoneClassName = [
    "wf-widget__dropzone",
    isDragging ? "is-active" : "",
    readOnly || isUploading ? "is-disabled" : "",
  ]
    .filter(Boolean)
    .join(" ");

  const dropzoneText = allowMultiple ? "Drag files here or click to browse." : "Drag a file here or click to browse.";
  const metaParts = [
    accept ? `Accepted: ${accept}` : null,
    maxBytes ? `Max ${formatBytes(maxBytes)}` : null,
  ].filter(Boolean);
  const dropzoneMeta = metaParts.length ? metaParts.join(" | ") : null;

  const handleRemove = async (resourceId: string) => {
    const next = resources.filter((item) => item.resourceId !== resourceId);
    applyChange(next);
    if (!deleteOnRemove) {
      return;
    }
    try {
      await resourcesGateway.delete(resourceId);
    } catch (deleteError) {
      const message = (deleteError as { message?: string })?.message ?? "Failed to delete resource.";
      setError(message);
    }
  };

  const handleDownload = async (resource: Resource) => {
    try {
      await resourcesGateway.download(resource.resourceId, resource.filename ?? undefined);
    } catch (downloadError) {
      const message = (downloadError as { message?: string })?.message ?? "Failed to download resource.";
      setError(message);
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
    } catch (previewError) {
      if (isAbortError(previewError)) {
        return;
      }
      const message = (previewError as { message?: string })?.message ?? "Failed to load preview.";
      setPreviewEntry(resourceId, { status: "error", kind, error: message });
      setError(message);
    } finally {
      previewControllersRef.current.delete(resourceId);
    }
  };

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

  return (
    <div className="wf-widget wf-widget--file-upload">
      <div className="wf-widget__label">
        <span>{widget.label}</span>
        <label
          className={dropzoneClassName}
          onDragEnter={handleDragEnter}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onDragOver={handleDragOver}
        >
          <input
            className="wf-widget__file-input"
            type="file"
            accept={accept}
            multiple={allowMultiple}
            onChange={handleUpload}
            disabled={readOnly || isUploading}
          />
          <span className="wf-widget__dropzone-text">{dropzoneText}</span>
          {dropzoneMeta && <span className="wf-widget__dropzone-meta">{dropzoneMeta}</span>}
        </label>
      </div>
      {helperText && <div className="wf-widget__hint">{helperText}</div>}
      {isUploading && <div className="wf-widget__hint">Uploading...</div>}
      {error && <div className="wf-widget__error">{error}</div>}
      {uploads.length > 0 && (
        <ul className="wf-widget__upload-list">
          {uploads.map((entry) => {
            const progressPct = Math.round(Math.min(100, Math.max(0, entry.progress * 100)));
            const status =
              entry.status === "error"
                ? "Failed"
                : entry.status === "paused"
                  ? "Paused"
                : entry.status === "queued"
                  ? "Queued"
                  : `${progressPct}%`;
            return (
              <li key={entry.key} className="wf-widget__upload-item">
                <div className="wf-widget__upload-header">
                  <span className="wf-widget__upload-name">{entry.name}</span>
                  <span className="wf-widget__upload-meta">{formatBytes(entry.size)}</span>
                  <span className="wf-widget__upload-status">{status}</span>
                  <div className="wf-widget__upload-actions">
                    {entry.status === "uploading" && (
                      <>
                        <button
                          type="button"
                          className="wf-widget__upload-action wf-widget__upload-action--cancel"
                          onClick={() => handlePauseUpload(entry.key)}
                        >
                          Pause
                        </button>
                        <button
                          type="button"
                          className="wf-widget__upload-action wf-widget__upload-action--remove"
                          onClick={() => handleCancelUpload(entry.key)}
                        >
                          Cancel
                        </button>
                      </>
                    )}
                    {entry.status === "queued" && (
                      <button
                        type="button"
                        className="wf-widget__upload-action wf-widget__upload-action--remove"
                        onClick={() => handleDismissUpload(entry.key)}
                      >
                        Remove
                      </button>
                    )}
                    {entry.status === "paused" && (
                      <>
                        <button
                          type="button"
                          className="wf-widget__upload-action wf-widget__upload-action--retry"
                          onClick={() => handleRetryUpload(entry.key)}
                        >
                          Resume
                        </button>
                        <button
                          type="button"
                          className="wf-widget__upload-action wf-widget__upload-action--remove"
                          onClick={() => handleCancelUpload(entry.key)}
                        >
                          Remove
                        </button>
                      </>
                    )}
                    {entry.status === "error" && (
                      <>
                        <button
                          type="button"
                          className="wf-widget__upload-action wf-widget__upload-action--retry"
                          onClick={() => handleRetryUpload(entry.key)}
                        >
                          Retry
                        </button>
                        <button
                          type="button"
                          className="wf-widget__upload-action wf-widget__upload-action--remove"
                          onClick={() => handleDismissUpload(entry.key)}
                        >
                          Remove
                        </button>
                      </>
                    )}
                  </div>
                </div>
                <div className="wf-widget__upload-bar">
                  <div className="wf-widget__upload-progress" style={{ width: `${progressPct}%` }} />
                </div>
                {entry.error && <div className="wf-widget__upload-error">{entry.error}</div>}
              </li>
            );
          })}
        </ul>
      )}
      {resources.length > 0 && (
        <ul className="wf-widget__file-list">
          {resources.map((resource) => {
            const previewKind = inferPreviewKind(resource);
            const preview = previews[resource.resourceId];
            return (
              <li key={resource.resourceId} className="wf-widget__file-item">
                <span className="wf-widget__file-name">{resource.filename ?? resource.resourceId}</span>
                <span className="wf-widget__file-meta">{formatBytes(resource.sizeBytes)}</span>
                {previewKind && (
                  <button
                    type="button"
                    className={`wf-widget__file-link${preview ? " is-active" : ""}`}
                    onClick={() => handleTogglePreview(resource)}
                  >
                    {preview?.status === "loading"
                      ? "Loading"
                      : preview
                        ? "Hide"
                        : "Preview"}
                  </button>
                )}
                {resource.downloadUrl && (
                  <button
                    type="button"
                    className="wf-widget__file-link"
                    onClick={() => handleDownload(resource)}
                  >
                    Download
                  </button>
                )}
                {!readOnly && (
                  <button
                    type="button"
                    className="wf-widget__file-remove"
                    onClick={() => handleRemove(resource.resourceId)}
                  >
                    Remove
                  </button>
                )}
                {preview && (
                  <div className="wf-widget__file-preview">
                    {preview.status === "loading" && <span>Loading preview...</span>}
                    {preview.status === "error" && (
                      <span className="wf-widget__file-preview-error">{preview.error}</span>
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
                )}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
};
