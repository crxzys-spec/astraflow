const STORAGE_KEY = "astraflow.activeRunMap";

type ActiveRunMap = Record<string, string>;

const canUseStorage = () =>
  typeof window !== "undefined" && typeof window.localStorage !== "undefined";

const readMap = (): ActiveRunMap => {
  if (!canUseStorage()) {
    return {};
  }
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return {};
    }
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== "object") {
      return {};
    }
    const entries = Object.entries(parsed as Record<string, unknown>);
    const map: ActiveRunMap = {};
    entries.forEach(([key, value]) => {
      if (typeof value === "string") {
        map[key] = value;
      }
    });
    return map;
  } catch {
    return {};
  }
};

const writeMap = (map: ActiveRunMap) => {
  if (!canUseStorage()) {
    return;
  }
  try {
    const keys = Object.keys(map);
    if (keys.length === 0) {
      window.localStorage.removeItem(STORAGE_KEY);
      return;
    }
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(map));
  } catch {
    // Ignore storage failures; playback can still operate in-memory.
  }
};

export const getStoredActiveRunId = (workflowId?: string | null): string | null => {
  if (!workflowId || workflowId === "new") {
    return null;
  }
  const map = readMap();
  return map[workflowId] ?? null;
};

export const setStoredActiveRunId = (
  workflowId?: string | null,
  runId?: string | null,
): void => {
  if (!workflowId || workflowId === "new") {
    return;
  }
  const map = readMap();
  if (!runId) {
    delete map[workflowId];
  } else {
    map[workflowId] = runId;
  }
  writeMap(map);
};
