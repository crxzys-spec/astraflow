type HubBrowseTab = "packages" | "workflows" | "orgs";

const normalizeBase = (value: string) => value.replace(/\/+$/, "");

const tabPathMap: Record<HubBrowseTab, string> = {
  packages: "/packages",
  workflows: "/workflows",
  orgs: "/console/orgs",
};

const buildHubUrl = (
  base: string,
  params: { tab?: HubBrowseTab; id?: string },
): string => {
  const normalized = normalizeBase(base);
  if (!params.tab) {
    return normalized;
  }
  const tabPath = tabPathMap[params.tab];
  const baseWithTab = normalized.endsWith(tabPath)
    ? normalized
    : `${normalized}${tabPath}`;
  if (!params.id || params.tab === "orgs") {
    return baseWithTab;
  }
  const encodedId = encodeURIComponent(params.id);
  return `${baseWithTab}/${encodedId}`;
};

export const getHubWebBaseUrl = (): string | null => {
  const raw = import.meta.env.VITE_HUB_WEB_URL;
  if (!raw) {
    return null;
  }
  return normalizeBase(raw);
};

export const getHubBrowseUrl = (tab?: HubBrowseTab): string | null => {
  const base = getHubWebBaseUrl();
  if (!base) {
    return null;
  }
  return buildHubUrl(base, { tab });
};

export const getHubItemUrl = (tab: HubBrowseTab, id: string): string | null => {
  const base = getHubWebBaseUrl();
  if (!base) {
    return null;
  }
  return buildHubUrl(base, { tab, id });
};
