import { UsersApi } from "../client/apis/users-api";
import type { CreateUserRequest, UserList, UserRoleRequest } from "../client/models";
import { createApi } from "../api/client";
import { apiRequest } from "../api/fetcher";

const usersApi = createApi(UsersApi);

export const listUsers = async (): Promise<UserList> => {
  const response = await apiRequest(() => usersApi.listUsers());
  return response.data;
};

export const createUser = async (data: CreateUserRequest) => {
  const response = await apiRequest(() => usersApi.createUser(data));
  return response.data;
};

export const resetUserPassword = async (userId: string, password: string) => {
  await apiRequest(() => usersApi.resetUserPassword(userId, { password }));
};

export const addUserRole = async (userId: string, data: UserRoleRequest) => {
  await apiRequest(() => usersApi.addUserRole(userId, data));
};

export const removeUserRole = async (userId: string, role: string) => {
  await apiRequest(() => usersApi.removeUserRole(userId, role));
};

export const updateUserStatus = async (userId: string, isActive: boolean) => {
  await apiRequest(() => usersApi.updateUserStatus(userId, { isActive }));
};
