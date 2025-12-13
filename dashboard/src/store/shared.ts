export type ResourceStatus = "idle" | "loading" | "success" | "error";

export const buildKey = (...parts: Array<string | number | null | undefined>): string =>
  parts.map((part) => (part ?? "").toString()).join("|");

export const isCacheFresh = (
  updatedAt: number | undefined,
  staleAfter: number,
  now: number,
  force?: boolean,
): boolean => Boolean(updatedAt && !force && updatedAt + staleAfter > now);
