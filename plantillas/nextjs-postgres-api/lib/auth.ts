"use server";

import { cookies } from "next/headers";

export async function getAccessToken() {
  return (await cookies()).get("access_token")?.value;
}

export async function getRefreshToken() {
  return (await cookies()).get("refresh_token")?.value;
}

export async function setTokens(access: string, refresh: string) {
  const store = await cookies();
  store.set("access_token",  access,  { httpOnly: true, path: "/", maxAge: 60 * 30 });
  store.set("refresh_token", refresh, { httpOnly: true, path: "/", maxAge: 60 * 60 * 24 * 7 });
}

export async function clearTokens() {
  const store = await cookies();
  store.delete("access_token");
  store.delete("refresh_token");
}
