import axiosInstance from "../lib/setupAxios";
import { Configuration } from "../client";

type ApiConstructor<T> = new (config?: Configuration, basePath?: string, axios?: typeof axiosInstance) => T;

const resolveBasePath = () => {
  const envBase = import.meta.env.VITE_SCHEDULER_BASE_URL;
  if (!envBase) {
    return ""; // generated paths already include /api
  }
  try {
    const origin = typeof window !== "undefined" ? window.location.origin : envBase;
    const parsed = new URL(envBase, origin);
    if (typeof window !== "undefined" && window.location.protocol === "https:" && parsed.protocol === "http:") {
      console.warn("[api/client] Insecure API base under HTTPS, using relative base.");
      return "";
    }
    const path = parsed.pathname.replace(/\/+$/, "");
    return path === "/api" ? "" : path;
  } catch (error) {
    console.warn("[api/client] Invalid VITE_SCHEDULER_BASE_URL, using empty basePath", error);
    return "";
  }
};

const basePath = resolveBasePath();

// Shared configuration for all generated API classes; uses the global axios with auth interceptors.
export const configuration = new Configuration({
  basePath,
});

/**
 * Create an API instance wired to the shared axios (with bearer token interceptors)
 * and configuration (basePath from env/axios defaults).
 */
export const createApi = <T>(Api: ApiConstructor<T>, config: Configuration = configuration): T =>
  new Api(config, config.basePath, axiosInstance);

export { axiosInstance as apiAxios };
