import { usersService } from "@/services/users";
import { getAccessToken } from "@/lib/auth";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import Link from "next/link";
import { redirect } from "next/navigation";
import type { UserListItem } from "@/types";

export default async function UsersPage() {
  const token = await getAccessToken();
  let users: UserListItem[] = [];
  let errorMsg = "";

  try {
    users = await usersService.list(token!);
  } catch (e) {
    if (e instanceof Error && e.message.includes("401")) {
      redirect("/login");
    }
    errorMsg = e instanceof Error ? e.message : "Error al cargar usuarios";
  }

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Usuarios</h2>
          <p className="text-sm text-gray-500">{users.length} usuarios registrados</p>
        </div>
        <Link href="/users/new">
          <Button>+ Nuevo usuario</Button>
        </Link>
      </div>

      {errorMsg && (
        <div className="mb-4 rounded-lg bg-red-50 p-4 text-sm text-red-600">{errorMsg}</div>
      )}

      <div className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-left text-xs font-medium uppercase tracking-wide text-gray-500">
            <tr>
              <th className="px-4 py-3">Nombre</th>
              <th className="px-4 py-3">Email</th>
              <th className="px-4 py-3">Estado</th>
              <th className="px-4 py-3">Rol</th>
              <th className="px-4 py-3"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {users.length === 0 && !errorMsg && (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-gray-400">
                  No hay usuarios. Crea el primero.
                </td>
              </tr>
            )}
            {users.map((user) => (
              <tr key={user.id} className="hover:bg-gray-50 transition-colors">
                <td className="px-4 py-3 font-medium text-gray-900">
                  {user.full_name ?? "—"}
                  {user.is_superuser && (
                    <span className="ml-2 text-xs text-indigo-500">⚡ Super</span>
                  )}
                </td>
                <td className="px-4 py-3 text-gray-600">{user.email}</td>
                <td className="px-4 py-3">
                  <Badge
                    label={user.is_active ? "Activo" : "Inactivo"}
                    color={user.is_active ? "green" : "red"}
                  />
                </td>
                <td className="px-4 py-3 text-gray-500">
                  {user.is_superuser ? "superadmin" : "—"}
                </td>
                <td className="px-4 py-3 text-right">
                  <Link href={`/users/${user.id}`} className="text-indigo-600 hover:underline text-xs">
                    Ver →
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
