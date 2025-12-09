import axios from "./setupAxios";
import type { AxiosRequestConfig } from "axios";

// Reuse the globally configured axios instance (base URL + auth interceptors).
const httpClient = axios;

export const client = async <TData>(config: AxiosRequestConfig): Promise<TData> => {
  const response = await httpClient.request<TData>(config);
  return response.data;
};

export type HttpClient = typeof httpClient;
