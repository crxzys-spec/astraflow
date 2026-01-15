const coerceString = (value: unknown): string | null => {
  if (typeof value !== "string") {
    return null;
  }
  const trimmed = value.trim();
  return trimmed.length ? trimmed : null;
};

const extractDetailMessage = (detail: unknown): string | null => {
  const detailString = coerceString(detail);
  if (detailString) {
    return detailString;
  }
  if (!detail || typeof detail !== "object") {
    return null;
  }
  const detailRecord = detail as Record<string, unknown>;
  return (
    coerceString(detailRecord.message) ??
    coerceString(detailRecord.error) ??
    coerceString(detailRecord.detail)
  );
};

export const resolveApiErrorMessage = (error: unknown, fallback: string): string => {
  const fallbackMessage = fallback || "Request failed.";
  if (!error || typeof error !== "object") {
    return fallbackMessage;
  }
  const record = error as { response?: { data?: unknown }; message?: string };
  const data = record.response?.data;
  if (typeof data === "string") {
    return data.trim() || fallbackMessage;
  }
  if (data && typeof data === "object") {
    const dataRecord = data as Record<string, unknown>;
    const detailMessage = extractDetailMessage(dataRecord.detail);
    if (detailMessage) {
      return detailMessage;
    }
    const directMessage =
      coerceString(dataRecord.message) ?? coerceString(dataRecord.error);
    if (directMessage) {
      return directMessage;
    }
  }
  const errorMessage = coerceString(record.message);
  return errorMessage ?? fallbackMessage;
};

