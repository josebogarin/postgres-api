import { NextRequest, NextResponse } from "next/server";
import { setTokens } from "@/lib/auth";
import { authService } from "@/services/auth";

export async function POST(req: NextRequest) {
  const { email, password } = await req.json();

  try {
    const { access_token, refresh_token } = await authService.login(email, password);
    await setTokens(access_token, refresh_token);
    return NextResponse.json({ ok: true });
  } catch (e) {
    const msg = e instanceof Error ? e.message : "Login failed";
    return NextResponse.json({ detail: msg }, { status: 401 });
  }
}
