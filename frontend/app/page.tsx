import { redirect } from "next/navigation";
import { getAccessToken } from "@/lib/auth";

export default async function Home() {
  const token = await getAccessToken();
  if (token) redirect("/users");
  redirect("/login");
}
