"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import type { TorneoActivo } from "@/lib/types";

// Normaliza la respuesta de /api/v1/torneo/activas (array o {torneos|activas:[...]}).
function normalizeTorneos(raw: unknown): TorneoActivo[] {
  const box = raw as { torneos?: unknown[]; activas?: unknown[] } | unknown[];
  const arr: unknown[] = Array.isArray(box)
    ? box
    : Array.isArray((box as { torneos?: unknown[] })?.torneos)
    ? (box as { torneos: unknown[] }).torneos
    : Array.isArray((box as { activas?: unknown[] })?.activas)
    ? (box as { activas: unknown[] }).activas
    : [];
  return arr
    .map((x) => {
      const t = x as Record<string, unknown>;
      const estado = (t.estado as string) ?? null;
      const cerrado = Boolean(t.cerrado ?? t.terminado) || estado === "finalizado";
      return {
        id: Number(t.id ?? t.torneo_id),
        nombre: String(t.nombre ?? t.titulo ?? t.competicion ?? `Torneo ${t.id ?? ""}`),
        anio: t.anio != null ? Number(t.anio) : undefined,
        estado,
        cerrado,
        tipo: (t.tipo as string) ?? null,
        emoji: (t.emoji as string) ?? null,
        categoria: (t.categoria as string) ?? null,
        tiene_tercer_puesto: t.tiene_tercer_puesto as boolean | undefined,
        datos_cargados: t.datos_cargados as boolean | undefined,
        total_partidos: t.total_partidos as number | undefined,
        partidos_grupos: t.partidos_grupos as number | undefined,
        partidos_ko: t.partidos_ko as number | undefined,
        fecha_inicio: (t.fecha_inicio as string) ?? null,
        fecha_fin: (t.fecha_fin as string) ?? null,
        estado_juego: (t.estado_juego as string) ?? undefined,
        estado_label: (t.estado_label as string) ?? undefined,
      } as TorneoActivo;
    })
    .filter((t) => Number.isFinite(t.id));
}

// Clubes = SIN partido por el 3er puesto (de semis directo a la final).
// Selecciones/paises = CON 3er puesto.
// competicion.tipo es 'clubes' | 'paises' (valor real de la BD). Fallback: nombre.
const RE_SELECCIONES = /mundial|world\s*cup|copa\s*del\s*mundo|eurocopa|\beuro\b|copa\s*am[eé]rica|naciones|nations/i;
const RE_CLUBES = /champions|libertadores|sudamericana|club/i;
function esTorneoClubes(t: TorneoActivo): boolean {
  const tipo = (t.tipo ?? t.categoria ?? "").toLowerCase();
  if (tipo === "clubes" || tipo === "club") return true;
  if (tipo === "paises" || tipo === "selecciones") return false;
  // Fallback por nombre si el tipo no viene.
  const s = t.nombre;
  if (RE_SELECCIONES.test(s)) return false;
  return RE_CLUBES.test(s);
}

type Estado =
  | { fase: "cargando" }
  | { fase: "ok"; torneos: TorneoActivo[] }
  | { fase: "error"; msg: string };

export default function Home() {
  const router = useRouter();
  const [estado, setEstado] = useState<Estado>({ fase: "cargando" });

  useEffect(() => {
    let vivo = true;
    api
      .get<unknown>(`/torneo/activas`)
      .then((raw) => vivo && setEstado({ fase: "ok", torneos: normalizeTorneos(raw) }))
      .catch((e) => vivo && setEstado({ fase: "error", msg: String(e) }));
    return () => {
      vivo = false;
    };
  }, []);

  const entrar = (t: TorneoActivo) => {
    localStorage.setItem("becbuc_torneo", String(t.id));
    localStorage.setItem("becbuc_torneo_nombre", t.nombre);
    const soloLectura = t.cerrado || t.estado_label === "concluido";
    localStorage.setItem("becbuc_torneo_ro", soloLectura ? "1" : "0");
    // Clubes = sin 3er puesto -> el bracket debe omitir P103.
    localStorage.setItem("becbuc_torneo_tercero", esTorneoClubes(t) ? "0" : "1");
    router.push("/playoff-live");
  };

  return (
    <main className="mx-auto w-full max-w-md px-4 py-6">
      <header className="mb-5 flex items-center gap-3">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src="/static/becbuc-logo.jpeg"
          alt="BECBUC"
          className="h-10 w-10 rounded-xl object-contain"
        />
        <div>
          <h1 className="text-lg font-bold leading-tight">BECBUC</h1>
          <p className="text-xs text-muted">Elegí un torneo para entrar</p>
        </div>
      </header>

      {estado.fase === "cargando" && (
        <p className="py-10 text-center text-sm text-muted">Cargando torneos…</p>
      )}

      {estado.fase === "error" && (
        <div className="flex items-center gap-2 rounded-xl border border-border bg-surface-2 px-3 py-2 text-xs">
          <span className="h-2 w-2 rounded-full bg-orange" />
          <span className="text-muted">Sin conexión con la API (¿uvicorn en :8000?)</span>
        </div>
      )}

      {estado.fase === "ok" && estado.torneos.length === 0 && (
        <p className="py-10 text-center text-sm text-muted">
          No hay torneos activos. Cargá uno desde el portal.
        </p>
      )}

      {estado.fase === "ok" && estado.torneos.length > 0 && (
        <div className="flex flex-col gap-3">
          {estado.torneos.map((t) => (
            <TorneoCard key={t.id} t={t} onEnter={() => entrar(t)} />
          ))}
        </div>
      )}

      <p className="mt-6 text-center text-[11px] text-muted">
        Interfaz nueva (beta) — la versión actual sigue disponible sin cambios.
      </p>
    </main>
  );
}

const ESTADO_LABEL: Record<string, { txt: string; cls: string }> = {
  en_ejecucion: { txt: "En ejecución", cls: "bg-brand/20 text-brand" },
  pendiente: { txt: "Pendiente", cls: "bg-amber-400/15 text-amber-400" },
  concluido: { txt: "Concluido", cls: "bg-surface-2 text-muted" },
};
const ESTADO_JUEGO: Record<string, string> = {
  grupos: "fase de grupos",
  playoffs: "playoffs",
  terminada: "finalizado",
  pendiente: "aún no arranca",
};
function fdmy(iso?: string | null): string | null {
  if (!iso) return null;
  const s = iso.endsWith("Z") || iso.includes("+") ? iso : iso + "Z";
  const d = new Date(s);
  if (isNaN(d.getTime())) return null;
  return d.toLocaleDateString("es", { day: "2-digit", month: "2-digit", year: "2-digit" });
}

function TorneoCard({ t, onEnter }: { t: TorneoActivo; onEnter: () => void }) {
  const esClubes = esTorneoClubes(t);
  const icono = t.emoji || (esClubes ? "🏟️" : "🏆");
  const label = ESTADO_LABEL[t.estado_label ?? ""] ?? ESTADO_LABEL.pendiente;
  const ini = fdmy(t.fecha_inicio);
  const fin = fdmy(t.fecha_fin);
  const fechas = ini && fin ? `${ini} – ${fin}` : ini || fin || null;
  return (
    <button
      onClick={onEnter}
      className="flex items-center gap-3 rounded-2xl border border-border bg-surface p-4 text-left transition active:scale-[0.99]"
    >
      <span className="text-2xl">{icono}</span>
      <span className="min-w-0 flex-1">
        <span className="block truncate font-semibold">{t.nombre}</span>
        <span className="block truncate text-xs text-muted">
          {esClubes ? "Clubes" : "Selecciones"}
          {t.estado_juego ? ` · ${ESTADO_JUEGO[t.estado_juego] ?? t.estado_juego}` : ""}
        </span>
        <span className="block truncate text-[11px] text-muted">
          {t.total_partidos ? `${t.total_partidos} partidos` : "sin fixtures"}
          {fechas ? ` · ${fechas}` : ""}
        </span>
      </span>
      <span className={`shrink-0 rounded-full px-2 py-0.5 text-[10px] font-semibold ${label.cls}`}>
        {label.txt}
      </span>
      <span className="ml-1 shrink-0 text-muted">›</span>
    </button>
  );
}
