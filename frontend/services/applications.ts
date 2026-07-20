import { api } from "@/lib/api";
import type { Application } from "@/types";

export type AppCreatePayload = {
  slug: string;
  name: string;
  description?: string;
  db_url?: string;
  is_active?: boolean;
};

export type AppUpdatePayload = {
  name?: string;
  description?: string;
  db_url?: string;
  is_active?: boolean;
};

export const applicationsService = {
  list: (token: string) =>
    api.get<Application[]>("/applications/", token),

  get: (id: string, token: string) =>
    api.get<Application>(`/applications/${id}`, token),

  create: (payload: AppCreatePayload, token: string) =>
    api.post<Application>("/applications/", payload, token),

  update: (id: string, payload: AppUpdatePayload, token: string) =>
    api.patch<Application>(`/applications/${id}`, payload, token),

  remove: (id: string, token: string) =>
    api.delete<void>(`/applications/${id}`, token),
};
