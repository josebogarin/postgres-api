import { getAccessToken } from "@/lib/auth";
import { redirect } from "next/navigation";
import { authService } from "@/services/auth";

export default async function DashboardPage() {
  const token = await getAccessToken();
  if (!token) redirect("/login");

  const user = await authService.me(token).catch(() => null);

  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-900">Dashboard</h2>
      {user && (
        <p className="mt-2 text-sm text-gray-500">
          Bienvenido, <strong>{user.full_name ?? user.email}</strong>
        </p>
      )}
      <p className="mt-6 text-sm text-gray-400">
        Agregá tus páginas en <code className="font-mono">app/(dashboard)/</code>
      </p>
    </div>
  );
}
