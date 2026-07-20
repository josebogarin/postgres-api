import { api } from "@/lib/api";
import type { Token, User } from "@/types";

export const authService = {
  login: (email: string, password: string) =>
    api.post<Token>("/auth/login", { email, password }),

  refresh: (refresh_token: string) =>
    api.post<Token>("/auth/refresh", { refresh_token }),

  me: (token: string) =>
    api.get<User>("/auth/me", token),
};
