import { AuthApi } from "../client/apis/auth-api";
import type { AuthLoginRequest, AuthLoginResponse } from "../client/models";
import { createApi } from "../api/client";
import { apiRequest } from "../api/fetcher";

const authApi = createApi(AuthApi);

export const authLogin = async (payload: AuthLoginRequest): Promise<AuthLoginResponse> => {
  const response = await apiRequest(() => authApi.authLogin(payload));
  return response.data;
};
