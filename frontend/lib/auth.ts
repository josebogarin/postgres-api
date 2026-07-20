"use server";

import { cookies } from "next/headers";

const ACCESS_TOKEN = "access_token";
const REFRESH_TOKEN = "refresh_token";

export async function getAccessToken(): Promise<string | undefined> {
  const store = await cookies();
  return store.get(ACCESS_TOKEN)?.value;
}

export async function getRefreshToken(): Promise<string | undefined> {
  const store = await cookies();
  return store.get(REFRESH_TOKEN)?.value;
}

export async function setTokens(access: string, refresh: string) {
  const store = await cookies();
  store.set(ACCESS_TOKEN, access, { httpOnly: true, path: "/", maxAge: 60 * 30 });
  store.set(REFRESH_TOKEN, refresh, { httpOnly: true, path: "/", maxAge: 60 * 60 * 24 * 7 });
}

export async function clearTokens() {
  const store = await cookies();
  store.delete(ACCESS_TOKEN);
  store.delete(REFRESH_TOKEN);
}
