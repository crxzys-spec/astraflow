import type { AxiosResponse } from "axios";

type CacheEntry = {
  expiresAt: number;
  response: AxiosResponse;
};

const cache = new Map<string, CacheEntry>();

const isFresh = (entry: CacheEntry, now: number): boolean => entry.expiresAt > now;

export const getCachedResponse = <T = unknown>(key: string, now = Date.now()): AxiosResponse<T> | null => {
  const entry = cache.get(key);
  if (!entry) {
    return null;
  }
  if (!isFresh(entry, now)) {
    cache.delete(key);
    return null;
  }
  return entry.response as AxiosResponse<T>;
};

export const setCachedResponse = <T = unknown>(key: string, response: AxiosResponse<T>, ttlMs: number): void => {
  if (ttlMs <= 0) {
    return;
  }
  cache.set(key, { response, expiresAt: Date.now() + ttlMs });
};

export const clearResponseCache = (key?: string): void => {
  if (key) {
    cache.delete(key);
    return;
  }
  cache.clear();
};
