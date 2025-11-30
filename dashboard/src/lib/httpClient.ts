import axios from 'axios';
import type { AxiosRequestConfig } from 'axios';

const baseURL =
  import.meta.env.VITE_API_BASE_URL ||
  (typeof window !== 'undefined' ? window.location.origin : undefined) ||
  'http://127.0.0.1:8080';

const httpClient = axios.create({
  baseURL,
  headers: {
    'Content-Type': 'application/json'
  },
  withCredentials: false,
  timeout: 15000
});

httpClient.interceptors.request.use((config) => {
  // TODO: attach Authorization header when auth is integrated
  return config;
});

httpClient.interceptors.response.use(
  (response) => response,
  (error) => Promise.reject(error)
);

export const client = async <TData>(config: AxiosRequestConfig): Promise<TData> => {
  const response = await httpClient.request<TData>(config);
  return response.data;
};

export type HttpClient = typeof httpClient;


