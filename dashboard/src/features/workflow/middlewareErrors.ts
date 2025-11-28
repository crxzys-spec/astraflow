// Shared middleware next error codes surfaced by scheduler.
export const MIDDLEWARE_NEXT_ERROR_CODES = [
  "next_run_finalised",
  "next_duplicate",
  "next_no_chain",
  "next_invalid_chain",
  "next_target_not_ready",
  "next_timeout",
  "next_cancelled",
  "next_unavailable",
] as const;

export type MiddlewareNextErrorCode = (typeof MIDDLEWARE_NEXT_ERROR_CODES)[number];

export const middlewareNextErrorMessages: Record<string, string> = {
  next_run_finalised: "Run already finished.",
  next_duplicate: "Duplicate next request.",
  next_no_chain: "Middleware chain not found.",
  next_invalid_chain: "Invalid middleware chain index.",
  next_target_not_ready: "Next target not ready.",
  next_timeout: "Middleware next timed out.",
  next_cancelled: "Middleware next cancelled.",
  next_unavailable: "Middleware next unavailable.",
};
