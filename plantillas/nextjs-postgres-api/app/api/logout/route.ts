import { NextResponse } from "next/server";
import { clearTokens } from "@/lib/auth";

export async function POST() {
  await clearTokens();
  return NextResponse.redirect(new URL("/login", "http://localhost:3000"));
}
