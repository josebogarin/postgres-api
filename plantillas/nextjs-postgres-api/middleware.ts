import { NextRequest, NextResponse } from "next/server";

const PUBLIC_PATHS = ["/login", "/api/login"];

function isTokenExpired(token: string): boolean {
  try {
    const b64 = token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
    const payload = JSON.parse(atob(b64)) as { exp?: number };
    return !payload.exp || payload.exp < Date.now() / 1000;
  } catch {
    return true;
  }
}

async function tryRefresh(refreshToken: string): Promise<{ access_token: string; refresh_token: string } | null> {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL;
  if (!apiUrl) return null;
  try {
    const res = await fetch(`${apiUrl}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (!res.ok) return null;
    const data = await res.json();
    return data.access_token && data.refresh_token ? data : null;
  } catch {
    return null;
  }
}

function setTokenCookies(response: NextResponse, tokens: { access_token: string; refresh_token: string }) {
  response.cookies.set("access_token",  tokens.access_token,  { httpOnly: true, path: "/", maxAge: 60 * 30 });
  response.cookies.set("refresh_token", tokens.refresh_token, { httpOnly: true, path: "/", maxAge: 60 * 60 * 24 * 7 });
  return response;
}

function redirectToLogin(req: NextRequest): NextResponse {
  const url = req.nextUrl.clone();
  url.pathname = "/login";
  url.searchParams.set("next", req.nextUrl.pathname);
  const res = NextResponse.redirect(url);
  res.cookies.delete("access_token");
  res.cookies.delete("refresh_token");
  return res;
}

export async function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl;
  const isPublic     = PUBLIC_PATHS.some((p) => pathname.startsWith(p));
  const accessToken  = req.cookies.get("access_token")?.value;
  const refreshToken = req.cookies.get("refresh_token")?.value;

  // Ya autenticado intentando ir a /login → redirigir al dashboard
  if (pathname === "/login" && accessToken && !isTokenExpired(accessToken)) {
    return NextResponse.redirect(new URL("/dashboard", req.url));
  }

  if (isPublic) return NextResponse.next();

  // Token válido → continuar
  if (accessToken && !isTokenExpired(accessToken)) return NextResponse.next();

  // Token expirado → intentar refresh
  if (refreshToken) {
    const tokens = await tryRefresh(refreshToken);
    if (tokens) return setTokenCookies(NextResponse.next(), tokens);
  }

  return redirectToLogin(req);
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)" ],
};
