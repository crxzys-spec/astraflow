import { HubAccountApi } from "../client/apis/hub-account-api";
import type { HubAccount } from "../client/models";
import { createApi } from "../api/client";
import { apiRequest } from "../api/fetcher";

const hubAccountApi = createApi(HubAccountApi);

export const getHubAccount = async (): Promise<HubAccount> => {
  const response = await apiRequest(() => hubAccountApi.getHubAccount());
  return response.data as HubAccount;
};

export const hubAccountGateway = {
  get: getHubAccount,
};
