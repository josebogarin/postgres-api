import { NextRequest, NextResponse } from "next/server";
import { getAccessToken } from "@/lib/auth";
import { usersService } from "@/services/users";

export async function PATCH(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  const token = await getAccessToken();
  if (!token) return NextResponse.json({ detail: "No autorizado" }, { status: 401 });

  try {
    const { id } = await params;
    const body = await req.json();
    const user = await usersService.update(id, body, token);
    return NextResponse.json(user);
  } catch (e) {
    const msg = e instanceof Error ? e.message : "Error al actualizar usuario";
    return NextResponse.json({ detail: msg }, { status: 400 });
  }
}
