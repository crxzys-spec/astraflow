import type { UpdateUserProfileRequest, UserSummary } from "../client/models";
import { UsersApi } from "../client/apis/users-api";
import { createApi } from "../api/client";
import { apiRequest } from "../api/fetcher";

const usersApi = createApi(UsersApi);

export const getUserProfile = async (): Promise<UserSummary> => {
  const response = await apiRequest<UserSummary>((config) => usersApi.getUserProfile(config));
  return response.data;
};

export const updateUserProfile = async (
  payload: UpdateUserProfileRequest,
): Promise<UserSummary> => {
  const response = await apiRequest<UserSummary>((config) => usersApi.updateUserProfile(payload, config));
  return response.data;
};

export const accountGateway = {
  getProfile: getUserProfile,
  updateProfile: updateUserProfile,
};
