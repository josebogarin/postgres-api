// Cliente API compartido para BECBUC.
// - Mismo origen: en DEV, next.config proxya /api -> uvicorn :8000;
//   en EXPORT, el sitio se sirve por uvicorn (mismo origen que la API).
//   Por eso el base es relativo.
// - Header ngrok-skip-browser-warning para saltar el interstitial de ngrok.
// - Auto-login con las credenciales del sistema (igual que hacen hoy las
//   páginas live). TODO: reemplazar por un token público de solo-lectura.

const BASE = "/api/v1";

// Mismas credenciales que usan hoy becbuc-live*.html para auto-login.
const SYS_USER = "jose";
const SYS_PASS = "catalina";

const TOKEN_KEY = "becbuc_token";

const baseHeaders: Record<string, string> = {
  "ngrok-skip-browser-warning": "true",
};

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}
function setToken(t: string) {
  if (typeof window !== "undefined") window.localStorage.setItem(TOKEN_KEY, t);
}

export async function login(): Promise<string> {
  const r = await fetch(`${BASE}/auth/login`, {
    method: "POST",
    headers: { ...baseHeaders, "Content-Type": "application/json" },
    body: JSON.stringify({ username: SYS_USER, password: SYS_PASS }),
  });
  if (!r.ok) throw new Error(`login ${r.status}`);
  const data = await r.json();
  const tok = data.access_token as string;
  if (!tok) throw new Error("login sin token");
  setToken(tok);
  return tok;
}

async function ensureToken(): Promise<string> {
  return getToken() ?? (await login());
}

async function request<T>(
  path: string,
  opts: RequestInit = {},
  retry = true
): Promise<T> {
  const tok = await ensureToken();
  const r = await fetch(`${BASE}${path}`, {
    ...opts,
    headers: {
      ...baseHeaders,
      ...(opts.body ? { "Content-Type": "application/json" } : {}),
      Authorization: `Bearer ${tok}`,
      ...(opts.headers as Record<string, string> | undefined),
    },
  });
  if (r.status === 401 && retry) {
    await login();
    return request<T>(path, opts, false);
  }
  if (r.status === 204) return null as T;
  if (!r.ok) throw new Error(`${path} -> ${r.status}`);
  return (await r.json()) as T;
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "POST", body: body ? JSON.stringify(body) : undefined }),
};
