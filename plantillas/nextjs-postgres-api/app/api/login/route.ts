import { NextRequest, NextResponse } from "next/server";
import { setTokens } from "@/lib/auth";

export async function POST(req: NextRequest) {
  const { email, password } = await req.json();
  const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

  const res = await fetch(`${API}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    return NextResponse.json({ detail: err.detail ?? "Credenciales incorrectas" }, { status: 401 });
  }

  const { access_token, refresh_token } = await res.json();
  await setTokens(access_token, refresh_token);
  return NextResponse.json({ ok: true });
}
