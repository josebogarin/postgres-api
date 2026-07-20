import { NextResponse } from "next/server";
import { clearTokens } from "@/lib/auth";

export async function POST() {
  await clearTokens();
  return NextResponse.redirect(new URL("/login", process.env.NEXT_PUBLIC_APP_URL ?? "http://localhost:3000"));
  // NEXT_PUBLIC_APP_URL debe estar en .env.local en producción (ej: https://mi-app.com)
}
