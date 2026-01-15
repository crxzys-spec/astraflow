import i18n from "../i18n";

export type LocalizedText = string | Record<string, string> | null | undefined;

export const LOCALIZED_TEXT_DEFAULT_KEY = "default";

const normalizeLocale = (value: string) => value.toLowerCase().replace("_", "-");

const resolveLocaleKey = (locale: string | undefined, entries: Record<string, string>): string => {
  const trimmed = (locale ?? "").trim();
  if (!trimmed) {
    return LOCALIZED_TEXT_DEFAULT_KEY;
  }
  const normalized = normalizeLocale(trimmed);
  if (normalized === LOCALIZED_TEXT_DEFAULT_KEY) {
    return LOCALIZED_TEXT_DEFAULT_KEY;
  }
  const existing = Object.keys(entries).find((key) => normalizeLocale(key) === normalized);
  return existing ?? trimmed;
};

const pickDefaultEntry = (entries: Record<string, string>): string | undefined => {
  if (LOCALIZED_TEXT_DEFAULT_KEY in entries) {
    return entries[LOCALIZED_TEXT_DEFAULT_KEY];
  }
  const normalizedKeys = Object.keys(entries);
  const matchKey = (target: string) =>
    normalizedKeys.find((key) => normalizeLocale(key) === target);
  const preferred = matchKey("en") ?? matchKey("en-us");
  if (preferred) {
    return entries[preferred];
  }
  const fallbackKey = normalizedKeys.sort()[0];
  return fallbackKey ? entries[fallbackKey] : undefined;
};

export const coerceLocalizedTextMap = (
  value: LocalizedText,
  fallback?: string
): Record<string, string> | undefined => {
  if (value === null || value === undefined) {
    return fallback !== undefined ? { [LOCALIZED_TEXT_DEFAULT_KEY]: fallback } : undefined;
  }
  if (typeof value === "string") {
    return { [LOCALIZED_TEXT_DEFAULT_KEY]: value };
  }
  const entries = Object.entries(value).filter(([, entry]) => typeof entry === "string");
  if (!entries.length) {
    return fallback !== undefined ? { [LOCALIZED_TEXT_DEFAULT_KEY]: fallback } : undefined;
  }
  const normalized = Object.fromEntries(entries) as Record<string, string>;
  const defaultValue = normalized[LOCALIZED_TEXT_DEFAULT_KEY] ?? fallback ?? pickDefaultEntry(normalized);
  if (defaultValue !== undefined && normalized[LOCALIZED_TEXT_DEFAULT_KEY] !== defaultValue) {
    return { ...normalized, [LOCALIZED_TEXT_DEFAULT_KEY]: defaultValue };
  }
  return normalized;
};

export const updateLocalizedTextDefault = (
  value: LocalizedText,
  nextDefault: string
): Record<string, string> => {
  const base = coerceLocalizedTextMap(value) ?? {};
  return { ...base, [LOCALIZED_TEXT_DEFAULT_KEY]: nextDefault };
};

export const updateLocalizedTextLocale = (
  value: LocalizedText,
  locale: string | undefined,
  nextText: string
): Record<string, string> => {
  const base = coerceLocalizedTextMap(value) ?? {};
  const key = resolveLocaleKey(locale, base);
  return { ...base, [key]: nextText };
};

export const getLocalizedTextEntry = (
  value: LocalizedText,
  locale: string | undefined
): string | undefined => {
  if (value === null || value === undefined) {
    return undefined;
  }
  const normalizedLocale = normalizeLocale((locale ?? "").trim());
  const isDefault = !normalizedLocale || normalizedLocale === LOCALIZED_TEXT_DEFAULT_KEY;
  if (typeof value === "string") {
    return isDefault ? value : undefined;
  }
  const entries = Object.entries(value);
  for (const [key, entry] of entries) {
    if (typeof entry !== "string") {
      continue;
    }
    if (normalizeLocale(key) === normalizedLocale) {
      return entry;
    }
  }
  if (isDefault) {
    return value[LOCALIZED_TEXT_DEFAULT_KEY];
  }
  return undefined;
};

const resolveFallbackLocale = (): string => {
  const fallback = i18n.options.fallbackLng;
  if (typeof fallback === "string") {
    return fallback;
  }
  if (Array.isArray(fallback) && fallback.length) {
    return fallback[0] ?? "en";
  }
  if (fallback && typeof fallback === "object") {
    const first = Object.values(fallback).find((entry) => Array.isArray(entry) && entry.length);
    if (Array.isArray(first) && first.length) {
      return first[0] ?? "en";
    }
  }
  return "en";
};

const buildLocaleCandidates = (locale: string | undefined, fallback: string) => {
  const candidates: string[] = [];
  const pushCandidate = (value: string | undefined) => {
    if (value && !candidates.includes(value)) {
      candidates.push(value);
    }
  };
  const pushLocale = (value: string | undefined) => {
    if (!value) {
      return;
    }
    const normalized = normalizeLocale(value);
    pushCandidate(normalized);
    const base = normalized.split("-")[0];
    if (base && base !== normalized) {
      pushCandidate(base);
    }
  };
  pushLocale(locale);
  pushCandidate(LOCALIZED_TEXT_DEFAULT_KEY);
  pushLocale(fallback);
  if (!candidates.includes("en")) {
    candidates.push("en");
  }
  return candidates;
};

export const resolveLocalizedText = (
  value: LocalizedText,
  locale: string | undefined = i18n.resolvedLanguage || i18n.language,
  fallbackLocale: string = resolveFallbackLocale(),
): string | undefined => {
  if (value === null || value === undefined) {
    return undefined;
  }
  if (typeof value === "string") {
    return value;
  }
  const normalizedEntries = Object.entries(value).reduce<Record<string, string>>(
    (acc, [key, entry]) => {
      if (typeof entry === "string") {
        acc[normalizeLocale(key)] = entry;
      }
      return acc;
    },
    {},
  );
  const candidates = buildLocaleCandidates(locale, fallbackLocale);
  for (const candidate of candidates) {
    const entry = normalizedEntries[candidate];
    if (entry) {
      return entry;
    }
  }
  const localeKeys = Object.keys(normalizedEntries).sort();
  const baseCandidates: string[] = [];
  const pushBase = (value: string | undefined) => {
    if (!value) {
      return;
    }
    const base = normalizeLocale(value).split("-")[0];
    if (base && !baseCandidates.includes(base)) {
      baseCandidates.push(base);
    }
  };
  pushBase(locale);
  pushBase(fallbackLocale);
  for (const base of baseCandidates) {
    const match = localeKeys.find((key) => key.startsWith(`${base}-`));
    if (match) {
      return normalizedEntries[match];
    }
  }
  const firstKey = Object.keys(normalizedEntries).sort()[0];
  return firstKey ? normalizedEntries[firstKey] : undefined;
};
