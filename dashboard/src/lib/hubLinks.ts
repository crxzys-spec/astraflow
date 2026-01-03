type HubBrowseTab = "packages" | "workflows" | "orgs";

const normalizeBase = (value: string) => value.replace(/\/+$/, "");

const buildHubUrl = (
  base: string,
  params: { tab?: HubBrowseTab; id?: string },
): string => {
  const [path, query] = base.split("?");
  const search = new URLSearchParams(query ?? "");
  if (params.tab) {
    search.set("tab", params.tab);
  }
  if (params.id) {
    search.set("id", params.id);
  }
  const queryString = search.toString();
  return queryString ? `${path}?${queryString}` : path;
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
