import type { AxiosError, AxiosRequestConfig, AxiosResponse } from "axios";
import { getCachedResponse, setCachedResponse } from "./responseCache";

export type ApiError = {
  message: string;
  status?: number;
  code?: string;
  details?: unknown;
  raw?: unknown;
};

export type ApiRequestOptions = {
  dedupeKey?: string;
  retry?: number;
  retryDelayMs?: number;
  maxRetryDelayMs?: number;
  signal?: AbortSignal;
  timeoutMs?: number;
  cacheKey?: string;
  cacheTtlMs?: number;
};

const inflight = new Map<string, Promise<AxiosResponse>>();

const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

const shouldRetry = (error: unknown): boolean => {
  const status = (error as { response?: { status?: number } })?.response?.status;
  return status === 429 || (typeof status === "number" && status >= 500);
};

const isAbortError = (error: unknown): boolean => {
  const code = (error as { code?: string })?.code;
  const name = (error as { name?: string })?.name;
  const message = (error as { message?: string })?.message;
  return code === "ERR_CANCELED" || name === "CanceledError" || message === "canceled";
};

const parseRetryAfterMs = (error: unknown): number | null => {
  const header = (error as { response?: { headers?: Record<string, string | number> } })?.response?.headers?.[
    "retry-after"
  ];
  if (!header) {
    return null;
  }
  const seconds = Number(header);
  if (Number.isFinite(seconds)) {
    return seconds * 1000;
  }
  const date = Date.parse(String(header));
  if (Number.isFinite(date)) {
    return Math.max(0, date - Date.now());
  }
  return null;
};

const computeRetryDelay = (
  attempt: number,
  baseDelayMs: number,
  maxDelayMs: number,
  retryAfterMs: number | null,
): number => {
  const expBackoff = baseDelayMs * 2 ** attempt;
  const jitter = Math.random() * baseDelayMs;
  const candidate = expBackoff + jitter;
  const withRetryAfter = retryAfterMs != null ? Math.max(candidate, retryAfterMs) : candidate;
  return Math.min(withRetryAfter, maxDelayMs);
};

export const toApiError = (error: unknown): ApiError => {
  if (isAbortError(error)) {
    return { message: "Request cancelled", raw: error };
  }
  if ((error as { isAxiosError?: boolean })?.isAxiosError) {
    const axiosError = error as AxiosError<{ message?: string; code?: string; details?: unknown }>;
    const status = axiosError.response?.status;
    const payload = axiosError.response?.data;
    return {
      message:
        payload?.message ??
        axiosError.message ??
        (status ? `Request failed with status ${status}` : "Request failed"),
      status,
      code: payload?.code ?? axiosError.code,
      details: payload?.details,
      raw: error,
    };
  }
  if (error instanceof Error) {
    return { message: error.message, raw: error };
  }
  return { message: "Unknown error", raw: error };
};

export const apiRequest = async <T>(
  request: (config?: AxiosRequestConfig) => Promise<AxiosResponse<T>>,
  options: ApiRequestOptions = {},
): Promise<AxiosResponse<T>> => {
  const {
    dedupeKey,
    retry = 0,
    retryDelayMs = 300,
    maxRetryDelayMs = 10_000,
    timeoutMs = 20_000,
    signal,
    cacheKey,
    cacheTtlMs,
  } = options;

  const execute = async (attempt: number): Promise<AxiosResponse<T>> => {
    try {
      const now = Date.now();
      if (cacheKey && cacheTtlMs && cacheTtlMs > 0) {
        const cached = getCachedResponse<T>(cacheKey, now);
        if (cached) {
          return cached;
        }
      }
      const response = await request({ signal, timeout: timeoutMs });
      if (cacheKey && cacheTtlMs && cacheTtlMs > 0) {
        setCachedResponse(cacheKey, response, cacheTtlMs);
      }
      return response;
    } catch (error) {
      if (!isAbortError(error) && attempt < retry && shouldRetry(error)) {
    const retryAfterMs = parseRetryAfterMs(error);
    const waitMs = computeRetryDelay(attempt, retryDelayMs, maxRetryDelayMs, retryAfterMs);
        if (waitMs > 0) {
          await delay(waitMs);
        }
        return execute(attempt + 1);
      }
      throw error;
    }
  };

  if (!dedupeKey) {
    return execute(0);
  }

  const existing = inflight.get(dedupeKey);
  if (existing) {
    return existing as Promise<AxiosResponse<T>>;
  }

  const promise = execute(0);
  inflight.set(dedupeKey, promise as Promise<AxiosResponse>);
  try {
    return await promise;
  } finally {
    inflight.delete(dedupeKey);
  }
};
