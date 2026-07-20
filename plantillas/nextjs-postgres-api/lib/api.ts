const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

async function request<T>(
  endpoint: string,
  options: { method?: string; body?: unknown; token?: string } = {},
): Promise<T> {
  const { method = "GET", body, token } = options;
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${API_URL}${endpoint}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
    cache: "no-store",
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail ?? "Request failed");
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export const api = {
  get:    <T>(url: string, token?: string)                  => request<T>(url, { token }),
  post:   <T>(url: string, body: unknown, token?: string)   => request<T>(url, { method: "POST",   body, token }),
  patch:  <T>(url: string, body: unknown, token?: string)   => request<T>(url, { method: "PATCH",  body, token }),
  delete: <T>(url: string, token?: string)                  => request<T>(url, { method: "DELETE", token }),
};
