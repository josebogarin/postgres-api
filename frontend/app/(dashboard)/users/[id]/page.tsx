import { usersService } from "@/services/users";
import { getAccessToken } from "@/lib/auth";
import { redirect, notFound } from "next/navigation";
import { UserDetail } from "./UserDetail";

export default async function UserPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const token = await getAccessToken();
  if (!token) redirect("/login");

  let user;
  try {
    user = await usersService.get(id, token);
  } catch (e) {
    if (e instanceof Error && e.message.includes("404")) notFound();
    redirect("/users");
  }

  return <UserDetail user={user} />;
}
