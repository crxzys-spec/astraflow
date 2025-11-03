const STORAGE_KEY = "astraflow.clientSessionId";

let cachedSessionId: string | null = null;

const fallbackRandomId = () =>
  `${Math.random().toString(16).slice(2)}${Date.now().toString(16)}`;

export const getClientSessionId = (): string => {
  if (cachedSessionId) {
    return cachedSessionId;
  }

  if (typeof window === "undefined" || typeof window.localStorage === "undefined") {
    cachedSessionId = fallbackRandomId();
    return cachedSessionId;
  }

  const existing = window.localStorage.getItem(STORAGE_KEY);
  if (existing) {
    cachedSessionId = existing;
    return cachedSessionId;
  }

  let generated: string;
  if (typeof window.crypto !== "undefined" && typeof window.crypto.randomUUID === "function") {
    generated = window.crypto.randomUUID();
  } else {
    generated = fallbackRandomId();
  }

  try {
    window.localStorage.setItem(STORAGE_KEY, generated);
  } catch (error) {
    // Ignore quota/security errors; fall back to in-memory cache
    console.warn("Unable to persist clientSessionId to localStorage", error);
  }

  cachedSessionId = generated;
  return cachedSessionId;
};

export const clearClientSessionId = (): void => {
  cachedSessionId = null;
  if (typeof window === "undefined" || typeof window.localStorage === "undefined") {
    return;
  }
  try {
    window.localStorage.removeItem(STORAGE_KEY);
  } catch (error) {
    console.warn("Unable to clear clientSessionId from localStorage", error);
  }
};
