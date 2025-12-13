import axiosInstance from "../lib/setupAxios";
import { Configuration } from "../client";

type ApiConstructor<T> = new (config?: Configuration, basePath?: string, axios?: typeof axiosInstance) => T;

const basePath =
  axiosInstance.defaults.baseURL ??
  import.meta.env.VITE_SCHEDULER_BASE_URL ??
  "/api";

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
