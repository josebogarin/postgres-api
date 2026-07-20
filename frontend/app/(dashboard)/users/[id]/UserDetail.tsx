"use client";

import { useState, FormEvent } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import Link from "next/link";
import type { User } from "@/types";

type Tab = "info" | "password";

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="mb-1.5 block text-sm font-medium text-gray-700">{label}</label>
      {children}
    </div>
  );
}

function inputCls(disabled?: boolean) {
  return `w-full rounded-lg border px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 ${
    disabled ? "border-gray-200 bg-gray-50 text-gray-500" : "border-gray-300 bg-white"
  }`;
}

export function UserDetail({ user }: { user: User }) {
  const router = useRouter();
  const [tab, setTab] = useState<Tab>("info");

  // ── Info tab state ──────────────────────────────────────────────────────────
  const [infoLoading, setInfoLoading] = useState(false);
  const [infoError, setInfoError]     = useState("");
  const [infoSuccess, setInfoSuccess] = useState("");

  // ── Password tab state ─────────────────────────────────────────────────────
  const [pwLoading, setPwLoading]   = useState(false);
  const [pwError, setPwError]       = useState("");
  const [pwSuccess, setPwSuccess]   = useState("");

  async function handleInfoSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setInfoLoading(true);
    setInfoError("");
    setInfoSuccess("");

    const form = new FormData(e.currentTarget);
    const payload = {
      full_name: form.get("full_name") as string || null,
      email: form.get("email") as string,
      is_active: form.get("is_active") === "on",
    };

    const res = await fetch(`/api/users/${user.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      setInfoError(data.detail ?? "Error al guardar los cambios");
    } else {
      setInfoSuccess("Cambios guardados correctamente");
      router.refresh();
    }
    setInfoLoading(false);
  }

  async function handlePasswordSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setPwLoading(true);
    setPwError("");
    setPwSuccess("");

    const form = new FormData(e.currentTarget);
    const newPw  = form.get("new_password") as string;
    const confirm = form.get("confirm_password") as string;

    if (newPw !== confirm) {
      setPwError("Las contraseñas no coinciden");
      setPwLoading(false);
      return;
    }
    if (newPw.length < 8) {
      setPwError("La contraseña debe tener al menos 8 caracteres");
      setPwLoading(false);
      return;
    }

    const res = await fetch(`/api/users/${user.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password: newPw }),
    });

    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      setPwError(data.detail ?? "Error al cambiar la contraseña");
    } else {
      setPwSuccess("Contraseña actualizada correctamente");
      (e.target as HTMLFormElement).reset();
    }
    setPwLoading(false);
  }

  return (
    <div className="mx-auto max-w-2xl">
      {/* Header */}
      <div className="mb-6 flex items-center gap-3">
        <Link href="/users" className="text-sm text-gray-500 hover:text-gray-700">
          ← Usuarios
        </Link>
        <span className="text-gray-300">/</span>
        <h2 className="text-xl font-bold text-gray-900">
          {user.full_name ?? user.email}
        </h2>
        <Badge
          label={user.is_active ? "Activo" : "Inactivo"}
          color={user.is_active ? "green" : "red"}
        />
        {user.is_superuser && (
          <span className="rounded-full bg-indigo-50 px-2 py-0.5 text-xs font-medium text-indigo-700">
            ⚡ Superusuario
          </span>
        )}
      </div>

      {/* Metadata strip */}
      <div className="mb-6 flex gap-6 rounded-xl border border-gray-200 bg-white px-5 py-4 text-sm text-gray-500 shadow-sm">
        <div><span className="font-medium text-gray-700">ID</span><br /><span className="font-mono text-xs">{user.id}</span></div>
        <div><span className="font-medium text-gray-700">Creado</span><br />{new Date(user.created_at).toLocaleDateString("es-CR")}</div>
        <div><span className="font-medium text-gray-700">Actualizado</span><br />{new Date(user.updated_at).toLocaleDateString("es-CR")}</div>
        <div>
          <span className="font-medium text-gray-700">Roles</span><br />
          {user.roles.length > 0
            ? user.roles.map((r) => r.name).join(", ")
            : <span className="text-gray-400">Sin roles</span>}
        </div>
      </div>

      {/* Tabs */}
      <div className="mb-1 flex border-b border-gray-200">
        {([["info", "Información"], ["password", "Contraseña"]] as [Tab, string][]).map(([key, label]) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={`px-5 py-2.5 text-sm font-medium transition-colors border-b-2 -mb-px ${
              tab === key
                ? "border-indigo-600 text-indigo-600"
                : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      <div className="rounded-b-xl rounded-tr-xl border border-t-0 border-gray-200 bg-white p-6 shadow-sm">
        {/* ── TAB: Información ─────────────────────────────────────────────── */}
        {tab === "info" && (
          <form onSubmit={handleInfoSubmit} className="flex flex-col gap-5">
            <Field label="Email">
              <input
                name="email"
                type="email"
                required
                defaultValue={user.email}
                className={inputCls()}
              />
            </Field>

            <Field label="Nombre completo">
              <input
                name="full_name"
                type="text"
                defaultValue={user.full_name ?? ""}
                className={inputCls()}
                placeholder="Sin nombre"
              />
            </Field>

            <div className="flex items-center gap-3 rounded-lg border border-gray-200 bg-gray-50 px-4 py-3">
              <input
                id="is_active"
                name="is_active"
                type="checkbox"
                defaultChecked={user.is_active}
                className="h-4 w-4 rounded border-gray-300 accent-indigo-600"
              />
              <div>
                <label htmlFor="is_active" className="text-sm font-medium text-gray-700 cursor-pointer">
                  Cuenta activa
                </label>
                <p className="text-xs text-gray-500">El usuario puede iniciar sesión en el sistema</p>
              </div>
            </div>

            <Field label="Superusuario">
              <input
                value={user.is_superuser ? "Sí — acceso total" : "No"}
                disabled
                className={inputCls(true)}
              />
              <p className="mt-1 text-xs text-gray-400">
                Para cambiar el rol de superusuario contacta a un administrador de base de datos.
              </p>
            </Field>

            {infoError && (
              <div className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-600">{infoError}</div>
            )}
            {infoSuccess && (
              <div className="rounded-lg bg-green-50 px-4 py-3 text-sm text-green-700">{infoSuccess}</div>
            )}

            <div className="flex justify-end gap-3 pt-2">
              <Button type="submit" loading={infoLoading}>Guardar cambios</Button>
            </div>
          </form>
        )}

        {/* ── TAB: Contraseña ──────────────────────────────────────────────── */}
        {tab === "password" && (
          <form onSubmit={handlePasswordSubmit} className="flex flex-col gap-5">
            <div className="rounded-lg bg-amber-50 px-4 py-3 text-sm text-amber-800">
              Estás cambiando la contraseña de <strong>{user.email}</strong>.
              El usuario deberá usar la nueva contraseña en su próximo inicio de sesión.
            </div>

            <Field label="Nueva contraseña">
              <input
                name="new_password"
                type="password"
                required
                minLength={8}
                autoComplete="new-password"
                className={inputCls()}
                placeholder="Mínimo 8 caracteres"
              />
            </Field>

            <Field label="Confirmar contraseña">
              <input
                name="confirm_password"
                type="password"
                required
                minLength={8}
                autoComplete="new-password"
                className={inputCls()}
                placeholder="Repite la contraseña"
              />
            </Field>

            {pwError && (
              <div className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-600">{pwError}</div>
            )}
            {pwSuccess && (
              <div className="rounded-lg bg-green-50 px-4 py-3 text-sm text-green-700">{pwSuccess}</div>
            )}

            <div className="flex justify-end gap-3 pt-2">
              <Button type="submit" loading={pwLoading} variant="danger">
                Cambiar contraseña
              </Button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
