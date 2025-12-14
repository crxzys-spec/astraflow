import axios from "axios";
import type { AxiosRequestHeaders } from "axios";
import { AUTH_STORAGE_KEY } from "../features/auth/constants";

const resolveBaseURL = () => {
  const envBase = import.meta.env.VITE_SCHEDULER_BASE_URL;
  if (!envBase) {
    return ""; // use relative paths with Vite proxy
  }
  try {
    const parsed = new URL(envBase, typeof window !== "undefined" ? window.location.origin : envBase);
    // Avoid duplicating /api prefix since generated paths already include it.
    const cleanPath = parsed.pathname.replace(/\/+$/, "");
    if (cleanPath === "/api") {
      parsed.pathname = "";
    } else {
      parsed.pathname = cleanPath;
    }
    return parsed.toString();
  } catch (error) {
    console.warn("[setupAxios] Invalid VITE_SCHEDULER_BASE_URL, using relative base", error);
    return "";
  }
};

axios.defaults.baseURL = resolveBaseURL();

let currentToken: string | null = null;

export const setAuthToken = (token?: string) => {
  currentToken = token ?? null;
  if (token) {
    axios.defaults.headers.common.Authorization = `Bearer ${token}`;
  } else {
    delete axios.defaults.headers.common.Authorization;
  }
};

export const getAuthToken = (): string | null => currentToken;

const devToken = import.meta.env.VITE_SCHEDULER_TOKEN;
if (devToken) {
  setAuthToken(devToken);
}

axios.interceptors.request.use((config) => {
  if (currentToken) {
    const headers = (config.headers ??= {} as AxiosRequestHeaders);
    if (!headers.Authorization) {
      headers.Authorization = `Bearer ${currentToken}`;
    }
  }
  return config;
});

axios.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error?.response?.status;
    if (status === 401) {
      const requestUrl = error?.config?.url ?? "";
      if (!requestUrl.includes("/api/v1/auth/login")) {
        window.localStorage.removeItem(AUTH_STORAGE_KEY);
        setAuthToken(undefined);
        if (window.location.pathname !== "/login") {
          window.location.replace("/login");
        }
      }
    }
    return Promise.reject(error);
  },
);

export default axios;
