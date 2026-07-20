import { NextRequest, NextResponse } from "next/server";

const PUBLIC_PATHS = ["/login", "/api/login"];

/** Decodifica el payload base64url de un JWT y comprueba si ha expirado. */
function isTokenExpired(token: string): boolean {
  try {
    const payloadB64 = token.split(".")[1];
    if (!payloadB64) return true;
    // base64url → base64 estándar
    const base64 = payloadB64.replace(/-/g, "+").replace(/_/g, "/");
    const json = atob(base64);
    const payload = JSON.parse(json) as { exp?: number };
    if (typeof payload.exp !== "number") return true;
    return payload.exp < Date.now() / 1000;
  } catch {
    return true;
  }
}

interface TokenPair {
  access_token: string;
  refresh_token: string;
}

/** Llama al endpoint de refresh y devuelve los nuevos tokens, o null si falla. */
async function refreshTokens(refreshToken: string): Promise<TokenPair | null> {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL;
  if (!apiUrl) return null;

  try {
    const res = await fetch(`${apiUrl}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    if (!res.ok) return null;

    const data = (await res.json()) as TokenPair;
    if (!data.access_token || !data.refresh_token) return null;

    return data;
  } catch {
    return null;
  }
}

/** Construye la URL de redirect a /login preservando el destino en ?next= */
function buildLoginRedirect(req: NextRequest): NextResponse {
  const loginUrl = req.nextUrl.clone();
  loginUrl.pathname = "/login";
  loginUrl.searchParams.set("next", req.nextUrl.pathname);
  return NextResponse.redirect(loginUrl);
}

/** Aplica las cookies de tokens en una respuesta con los mismos atributos que lib/auth.ts */
function applyTokenCookies(response: NextResponse, tokens: TokenPair): NextResponse {
  response.cookies.set("access_token", tokens.access_token, {
    httpOnly: true,
    path: "/",
    maxAge: 60 * 30, // 30 min
  });
  response.cookies.set("refresh_token", tokens.refresh_token, {
    httpOnly: true,
    path: "/",
    maxAge: 60 * 60 * 24 * 7, // 7 días
  });
  return response;
}

export async function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl;

  const isPublic = PUBLIC_PATHS.some((p) => pathname.startsWith(p));
  const accessToken = req.cookies.get("access_token")?.value;
  const refreshToken = req.cookies.get("refresh_token")?.value;

  // Ruta pública: si ya tiene access token válido y va al login → redirigir al dashboard
  if (pathname === "/login" && accessToken && !isTokenExpired(accessToken)) {
    const dashboardUrl = req.nextUrl.clone();
    dashboardUrl.pathname = "/users";
    return NextResponse.redirect(dashboardUrl);
  }

  // Rutas públicas no necesitan validación de token
  if (isPublic) {
    return NextResponse.next();
  }

  // ── Ruta protegida ──────────────────────────────────────────────────────────

  // Caso 1: tiene access_token y NO está expirado → continuar
  if (accessToken && !isTokenExpired(accessToken)) {
    return NextResponse.next();
  }

  // Caso 2: access_token expirado o ausente → intentar refresh si hay refresh_token
  if (refreshToken) {
    const newTokens = await refreshTokens(refreshToken);

    if (newTokens) {
      // Refresh exitoso: continuar y setear las nuevas cookies en la respuesta
      const response = NextResponse.next();
      return applyTokenCookies(response, newTokens);
    }

    // Refresh fallido: limpiar cookies y redirigir a login
    const redirectResponse = buildLoginRedirect(req);
    redirectResponse.cookies.delete("access_token");
    redirectResponse.cookies.delete("refresh_token");
    return redirectResponse;
  }

  // Caso 3: no hay ningún token → redirigir a login
  return buildLoginRedirect(req);
}

export const config = {
  matcher: [
    /*
     * Aplica a todas las rutas excepto:
     * - _next/static  (assets estáticos)
     * - _next/image   (optimización de imágenes)
     * - favicon.ico
     */
    "/((?!_next/static|_next/image|favicon.ico).*)",
  ],
};
