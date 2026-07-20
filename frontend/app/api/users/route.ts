import { NextRequest, NextResponse } from "next/server";
import { getAccessToken } from "@/lib/auth";
import { usersService } from "@/services/users";

export async function POST(req: NextRequest) {
  const token = await getAccessToken();
  if (!token) return NextResponse.json({ detail: "No autorizado" }, { status: 401 });

  try {
    const body = await req.json();
    const user = await usersService.create(body, token);
    return NextResponse.json(user, { status: 201 });
  } catch (e) {
    const msg = e instanceof Error ? e.message : "Error al crear usuario";
    return NextResponse.json({ detail: msg }, { status: 400 });
  }
}
