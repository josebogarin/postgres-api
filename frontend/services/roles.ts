import { api } from "@/lib/api";
import type { Role } from "@/types";

export type RoleCreatePayload = { name: string; description?: string };
export type RoleUpdatePayload = { description?: string };

export const rolesService = {
  list: (token: string) =>
    api.get<Role[]>("/roles/", token),

  create: (payload: RoleCreatePayload, token: string) =>
    api.post<Role>("/roles/", payload, token),

  update: (id: string, payload: RoleUpdatePayload, token: string) =>
    api.patch<Role>(`/roles/${id}`, payload, token),

  remove: (id: string, token: string) =>
    api.delete<void>(`/roles/${id}`, token),
};
