import type { AxiosProgressEvent } from "axios";
import type { Resource, ResourceUploadInitRequest, ResourceUploadPart, ResourceUploadSession } from "../client/models";
import { apiAxios, createApi } from "../api/client";
import { apiRequest } from "../api/fetcher";
import { ResourcesApi } from "../client/apis/resources-api";
import { sha256File } from "../lib/crypto/sha256";

const resourcesApi = createApi(ResourcesApi);

const DEFAULT_CHUNK_SIZE = 8 * 1024 * 1024;
const MAX_CHUNK_SIZE = 64 * 1024 * 1024;
const DEFAULT_CHUNK_CONCURRENCY = 3;
const UPLOAD_CACHE_KEY = "astraflow.resource.uploads.v1";

type UploadResourceOptions = {
  onProgress?: (progress: number) => void;
  onHashProgress?: (progress: number) => void;
  signal?: AbortSignal;
  timeoutMs?: number;
  chunkSize?: number;
  chunkConcurrency?: number;
  preserveSession?: boolean;
  deduplicate?: boolean;
};

type UploadCacheEntry = {
  uploadId: string;
  filename: string;
  sizeBytes: number;
  chunkSize: number;
  updatedAt: number;
  sha256?: string;
};

type UploadCache = Record<string, UploadCacheEntry>;

let uploadCache: UploadCache | null = null;

const canUseStorage = () => {
  if (typeof window === "undefined") {
    return false;
  }
  try {
    return Boolean(window.localStorage);
  } catch {
    return false;
  }
};

const loadUploadCache = (): UploadCache => {
  if (uploadCache) {
    return uploadCache;
  }
  uploadCache = {};
  if (!canUseStorage()) {
    return uploadCache;
  }
  try {
    const raw = window.localStorage.getItem(UPLOAD_CACHE_KEY);
    if (raw) {
      uploadCache = JSON.parse(raw) as UploadCache;
    }
  } catch {
    uploadCache = {};
  }
  return uploadCache;
};

const persistUploadCache = () => {
  if (!canUseStorage() || !uploadCache) {
    return;
  }
  try {
    window.localStorage.setItem(UPLOAD_CACHE_KEY, JSON.stringify(uploadCache));
  } catch {
    // Ignore storage failures.
  }
};

const setUploadCacheEntry = (fingerprint: string, entry: UploadCacheEntry) => {
  const cache = loadUploadCache();
  cache[fingerprint] = entry;
  persistUploadCache();
};

const getUploadCacheEntry = (fingerprint: string): UploadCacheEntry | null => {
  const cache = loadUploadCache();
  return cache[fingerprint] ?? null;
};

const clearUploadCacheEntry = (fingerprint: string) => {
  const cache = loadUploadCache();
  if (cache[fingerprint]) {
    delete cache[fingerprint];
    persistUploadCache();
  }
};

const buildUploadFingerprint = (file: File) => `${file.name}:${file.size}:${file.lastModified}`;

const resolveChunkSize = (value?: number) => {
  if (!value || !Number.isFinite(value) || value <= 0) {
    return DEFAULT_CHUNK_SIZE;
  }
  return Math.min(MAX_CHUNK_SIZE, Math.floor(value));
};

const clampProgress = (value: number) => Math.min(1, Math.max(0, value));

const reportProgress = (value: number, options: UploadResourceOptions) => {
  if (options.onProgress) {
    options.onProgress(clampProgress(value));
  }
};

const isAbortError = (error: unknown) => {
  const code = (error as { code?: string })?.code;
  const name = (error as { name?: string })?.name;
  const message = (error as { message?: string })?.message;
  return code === "ERR_CANCELED" || name === "CanceledError" || name === "AbortError" || message === "canceled";
};

const resolveFileSha256 = async (
  file: File,
  options: UploadResourceOptions,
): Promise<string | undefined> => {
  if (options.deduplicate === false) {
    return undefined;
  }
  return sha256File(file, { signal: options.signal, onProgress: options.onHashProgress });
};

const createUploadSession = async (
  file: File,
  chunkSize: number,
  sha256: string | undefined,
  options: UploadResourceOptions,
): Promise<ResourceUploadSession> => {
  const payload: ResourceUploadInitRequest = {
    filename: file.name,
    sizeBytes: file.size,
    mimeType: file.type || undefined,
    sha256: sha256 || undefined,
    chunkSize,
  };
  const response = await apiRequest<ResourceUploadSession>(
    (config) => resourcesApi.createResourceUpload(payload, config),
    { signal: options.signal, timeoutMs: options.timeoutMs },
  );
  return response.data;
};

const getUploadSession = async (
  uploadId: string,
  options: UploadResourceOptions,
): Promise<ResourceUploadSession> => {
  const response = await apiRequest<ResourceUploadSession>(
    (config) => resourcesApi.getResourceUpload(uploadId, config),
    { signal: options.signal, timeoutMs: options.timeoutMs },
  );
  return response.data;
};

const cacheUploadSession = (fingerprint: string, session: ResourceUploadSession) => {
  setUploadCacheEntry(fingerprint, {
    uploadId: session.uploadId,
    filename: session.filename,
    sizeBytes: session.sizeBytes,
    chunkSize: session.chunkSize,
    updatedAt: Date.now(),
    sha256: session.sha256 ?? undefined,
  });
};

const abortUploadSession = async (uploadId: string) => {
  try {
    await apiRequest<void>((config) => resourcesApi.deleteResourceUpload(uploadId, config));
  } catch {
    // Best-effort cleanup; ignore abort failures.
  }
};

const resolveResumeSession = async (
  file: File,
  fingerprint: string,
  sha256: string | undefined,
  options: UploadResourceOptions,
): Promise<ResourceUploadSession | null> => {
  const cached = getUploadCacheEntry(fingerprint);
  if (!cached) {
    return null;
  }
  if (sha256 && cached.sha256 && cached.sha256 !== sha256) {
    clearUploadCacheEntry(fingerprint);
    return null;
  }
  try {
    const session = await getUploadSession(cached.uploadId, options);
    if (
      session.status !== "pending" ||
      session.sizeBytes !== file.size ||
      session.filename !== file.name
    ) {
      clearUploadCacheEntry(fingerprint);
      return null;
    }
    if (sha256 && session.sha256 && session.sha256 !== sha256) {
      clearUploadCacheEntry(fingerprint);
      return null;
    }
    cacheUploadSession(fingerprint, session);
    return session;
  } catch {
    clearUploadCacheEntry(fingerprint);
    return null;
  }
};

export const uploadResource = async (
  file: File,
  options: UploadResourceOptions = {},
): Promise<Resource> => {
  if (file.size <= 0) {
    throw new Error("File is empty.");
  }
  const timeoutMs = options.timeoutMs ?? 120_000;
  const requestedChunkSize = resolveChunkSize(options.chunkSize);
  const chunkConcurrency = Math.max(
    1,
    Math.floor(options.chunkConcurrency ?? DEFAULT_CHUNK_CONCURRENCY),
  );
  const fingerprint = buildUploadFingerprint(file);
  const fileSha256 = await resolveFileSha256(file, options);
  let session: ResourceUploadSession | null = null;
  try {
    session = await resolveResumeSession(file, fingerprint, fileSha256, { ...options, timeoutMs });
    if (!session) {
      session = await createUploadSession(file, requestedChunkSize, fileSha256, { ...options, timeoutMs });
    }
    cacheUploadSession(fingerprint, session);
    const uploadId = session.uploadId;
    if (!uploadId) {
      throw new Error("Upload session missing uploadId.");
    }
    const totalBytes = session.sizeBytes ?? file.size;
    const chunkSize = session.chunkSize ?? requestedChunkSize;
    let nextPart = session.nextPart ?? 0;
    let uploadedBytes = session.uploadedBytes ?? 0;
    const totalParts = session.totalParts ?? Math.ceil(totalBytes / chunkSize);
    const completedSet = new Set<number>();
    const completedParts = session.completedParts ?? [];
    completedParts.forEach((part) => {
      if (Number.isFinite(part) && part >= 0 && part < totalParts) {
        completedSet.add(part);
      }
    });

    reportProgress(uploadedBytes / totalBytes, options);

    const partQueue = completedSet.size
      ? Array.from({ length: totalParts }, (_, index) => index).filter((part) => !completedSet.has(part))
      : Array.from({ length: totalParts - nextPart }, (_, index) => nextPart + index);
    const inflightProgress = new Map<number, number>();
    let completedBytes = uploadedBytes;
    let stopped = false;
    let failure: unknown | null = null;

    const updateProgress = () => {
      const inflightTotal = Array.from(inflightProgress.values()).reduce((sum, value) => sum + value, 0);
      reportProgress((completedBytes + inflightTotal) / totalBytes, options);
    };

    const expectedPartSize = (partNumber: number) => {
      if (partNumber < totalParts - 1) {
        return chunkSize;
      }
      const remaining = totalBytes - chunkSize * (totalParts - 1);
      return remaining > 0 ? remaining : chunkSize;
    };

    let cursor = 0;
    const workerCount = Math.min(chunkConcurrency, partQueue.length);
    const workers = Array.from({ length: workerCount }, async () => {
      while (!stopped && cursor < partQueue.length) {
        const partNumber = partQueue[cursor];
        cursor += 1;
        if (partNumber === undefined) {
          break;
        }
        if (options.signal?.aborted) {
          throw new DOMException("Upload aborted", "AbortError");
        }
        const start = partNumber * chunkSize;
        const end = Math.min(start + chunkSize, totalBytes);
        const chunk = file.slice(start, end);
        const chunkFile = new File([chunk], file.name, {
          type: file.type || "application/octet-stream",
        });
        const onUploadProgress = options.onProgress
          ? (event: AxiosProgressEvent) => {
              const loaded = event.loaded ?? 0;
              inflightProgress.set(partNumber, loaded);
              updateProgress();
            }
          : undefined;
        try {
          const response = await apiRequest<ResourceUploadPart>(
            (config) =>
              resourcesApi.uploadResourcePart(uploadId, partNumber, chunkFile, {
                ...config,
                onUploadProgress,
              }),
            { signal: options.signal, timeoutMs },
          );
          const part = response.data;
          const partSize = expectedPartSize(partNumber);
          inflightProgress.delete(partNumber);
          completedBytes = Math.min(totalBytes, completedBytes + partSize);
          uploadedBytes = Math.max(uploadedBytes, part.uploadedBytes ?? completedBytes);
          nextPart = Math.max(nextPart, part.nextPart ?? nextPart);
          updateProgress();
        } catch (error) {
          inflightProgress.delete(partNumber);
          stopped = true;
          failure = error;
          updateProgress();
          return;
        }
      }
    });

    if (partQueue.length > 0) {
      await Promise.all(workers);
    }
    if (failure) {
      throw failure;
    }

    const completed = await apiRequest<Resource>(
      (config) => resourcesApi.completeResourceUpload(uploadId, config),
      { signal: options.signal, timeoutMs },
    );
    reportProgress(1, options);
    clearUploadCacheEntry(fingerprint);
    return completed.data;
  } catch (error) {
    if (session?.uploadId && options.signal?.aborted && isAbortError(error)) {
      if (!options.preserveSession) {
        await abortUploadSession(session.uploadId);
        clearUploadCacheEntry(fingerprint);
      }
    }
    throw error;
  }
};

export const getResource = async (resourceId: string): Promise<Resource> => {
  const response = await apiRequest<Resource>(() => resourcesApi.getResource(resourceId));
  return response.data;
};

export const deleteResource = async (resourceId: string): Promise<void> => {
  await apiRequest<void>(() => resourcesApi.deleteResource(resourceId));
};

export const abortUploadForFile = async (file: File): Promise<void> => {
  const fingerprint = buildUploadFingerprint(file);
  const cached = getUploadCacheEntry(fingerprint);
  if (!cached) {
    return;
  }
  await abortUploadSession(cached.uploadId);
  clearUploadCacheEntry(fingerprint);
};

const extractFilename = (headerValue?: string): string | null => {
  if (!headerValue) {
    return null;
  }
  const match = /filename\*?=(?:UTF-8''|")?([^\";]+)/i.exec(headerValue);
  if (!match || !match[1]) {
    return null;
  }
  try {
    return decodeURIComponent(match[1]);
  } catch {
    return match[1];
  }
};

export const fetchResourceBlob = async (
  resourceId: string,
  options: UploadResourceOptions = {},
): Promise<{ blob: Blob; filename: string | null }> => {
  const response = await apiRequest<Blob>((config) =>
    apiAxios.get(`/api/v1/resources/${resourceId}/download`, {
      ...config,
      responseType: "blob",
      timeout: config?.timeout ?? options.timeoutMs ?? 120_000,
    }),
  );
  const contentDisposition = response.headers?.["content-disposition"];
  const resolvedName = extractFilename(contentDisposition);
  return { blob: response.data, filename: resolvedName };
};

export const downloadResource = async (resourceId: string, filename?: string): Promise<void> => {
  const { blob, filename: headerName } = await fetchResourceBlob(resourceId);
  const resolvedName = filename || headerName || "download";
  const blobUrl = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = blobUrl;
  link.download = resolvedName;
  link.rel = "noreferrer";
  link.style.display = "none";
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(blobUrl);
};

export const resourcesGateway = {
  upload: uploadResource,
  get: getResource,
  download: downloadResource,
  fetchBlob: fetchResourceBlob,
  abortUpload: abortUploadForFile,
  delete: deleteResource,
};
