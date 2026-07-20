/**
 * Cliente HTTP para la API REST FastAPI.
 * Lee los tokens desde SecureStore y hace refresh automático.
 */

import * as SecureStore from "expo-secure-store";

const BASE_URL = process.env.EXPO_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

const KEYS = { access: "access_token", refresh: "refresh_token" };

// ── Token storage ────────────────────────────────────────────────────────────

export const tokenStorage = {
  getAccess:  () => SecureStore.getItemAsync(KEYS.access),
  getRefresh: () => SecureStore.getItemAsync(KEYS.refresh),
  set: async (access: string, refresh: string) => {
    await SecureStore.setItemAsync(KEYS.access, access);
    await SecureStore.setItemAsync(KEYS.refresh, refresh);
  },
  clear: async () => {
    await SecureStore.deleteItemAsync(KEYS.access);
    await SecureStore.deleteItemAsync(KEYS.refresh);
  },
};

// ── Refresh ──────────────────────────────────────────────────────────────────

async function tryRefresh(): Promise<string | null> {
  const refresh = await tokenStorage.getRefresh();
  if (!refresh) return null;
  const res = await fetch(`${BASE_URL}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refresh }),
  });
  if (!res.ok) { await tokenStorage.clear(); return null; }
  const data = await res.json();
  await tokenStorage.set(data.access_token, data.refresh_token);
  return data.access_token;
}

// ── Fetch con retry automático ───────────────────────────────────────────────

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
): Promise<T> {
  let token = await tokenStorage.getAccess();

  const doFetch = (t: string | null) =>
    fetch(`${BASE_URL}${path}`, {
      method,
      headers: {
        "Content-Type": "application/json",
        ...(t ? { Authorization: `Bearer ${t}` } : {}),
      },
      body: body ? JSON.stringify(body) : undefined,
    });

  let res = await doFetch(token);

  if (res.status === 401) {
    token = await tryRefresh();
    if (!token) throw new Error("Session expired. Please login again.");
    res = await doFetch(token);
  }

  if (res.status === 204) return undefined as T;
  const data = await res.json();
  if (!res.ok) throw new Error(data?.detail ?? `HTTP ${res.status}`);
  return data as T;
}

// ── API pública ───────────────────────────────────────────────────────────────

export const api = {
  get:    <T>(path: string) => request<T>("GET", path),
  post:   <T>(path: string, body: unknown) => request<T>("POST", path, body),
  patch:  <T>(path: string, body: unknown) => request<T>("PATCH", path, body),
  delete: (path: string) => request<void>("DELETE", path),
};
