import { api } from "@/lib/api";
import type { User, UserListItem } from "@/types";

export type UserCreatePayload = {
  email: string;
  password: string;
  full_name?: string;
  is_superuser?: boolean;
};

export type UserUpdatePayload = {
  full_name?: string;
  email?: string;
  is_active?: boolean;
  password?: string;
};

export const usersService = {
  list:        (token: string)                                      => api.get<UserListItem[]>("/users/", token),
  get:         (id: string, token: string)                          => api.get<User>(`/users/${id}`, token),
  create:      (payload: UserCreatePayload, token: string)          => api.post<User>("/users/", payload, token),
  update:      (id: string, payload: UserUpdatePayload, token: string) => api.patch<User>(`/users/${id}`, payload, token),
  remove:      (id: string, token: string)                          => api.delete<void>(`/users/${id}`, token),
  assignRole:  (userId: string, roleId: string, token: string)      => api.post<User>(`/users/${userId}/roles`, { role_id: roleId }, token),
  removeRole:  (userId: string, roleId: string, token: string)      => api.delete<User>(`/users/${userId}/roles/${roleId}`, token),
};
