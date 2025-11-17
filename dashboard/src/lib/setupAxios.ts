import axios from "axios";
import type { AxiosRequestHeaders } from "axios";

const baseURL = import.meta.env.VITE_SCHEDULER_BASE_URL ?? "http://127.0.0.1:8080";
axios.defaults.baseURL = baseURL;

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

export default axios;
