export const toStringValue = (value: unknown): string =>
  value === undefined || value === null ? "" : String(value);

export const toNumberValue = (value: unknown): number | "" => {
  if (value === undefined || value === null || value === "") {
    return "";
  }
  const numeric = Number(value);
  return Number.isNaN(numeric) ? "" : numeric;
};
