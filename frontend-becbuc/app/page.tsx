"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { TORNEO_ID, type TorneoCerrado } from "@/lib/types";

type Estado =
  | { fase: "cargando" }
  | { fase: "ok"; cerrado: boolean }
  | { fase: "error"; msg: string };

export default function Home() {
  const [estado, setEstado] = useState<Estado>({ fase: "cargando" });

  useEffect(() => {
    let vivo = true;
    api
      .get<TorneoCerrado>(`/bets/torneo-cerrado/${TORNEO_ID}`)
      .then((d) => vivo && setEstado({ fase: "ok", cerrado: !!d?.cerrado }))
      .catch((e) => vivo && setEstado({ fase: "error", msg: String(e) }));
    return () => {
      vivo = false;
    };
  }, []);

  return (
    <main className="mx-auto w-full max-w-md px-4 py-6">
      <header className="mb-5 flex items-center gap-3">
        <div className="grid h-10 w-10 place-items-center rounded-xl bg-brand font-bold text-black">
          B
        </div>
        <div>
          <h1 className="text-lg font-bold leading-tight">BECBUC</h1>
          <p className="text-xs text-muted">Live y pronósticos</p>
        </div>
      </header>

      <div className="mb-4 flex flex-col gap-3">
        <SurfaceCard
          href="/playoff-live"
          title="Playoff Live"
          desc="Bracket, mi pronóstico y ranking de playoffs en vivo"
          emoji="🏆"
        />
        <SurfaceCard
          href="/grupos-live"
          title="Grupos Live"
          desc="Seguimiento en vivo de la fase de grupos"
          emoji="⚽"
        />
      </div>

      <ApiStatus estado={estado} />

      <p className="mt-6 text-center text-[11px] text-muted">
        Interfaz nueva (beta) — la versión actual sigue disponible sin cambios.
      </p>
    </main>
  );
}

function SurfaceCard({
  href,
  title,
  desc,
  emoji,
}: {
  href: string;
  title: string;
  desc: string;
  emoji: string;
}) {
  return (
    <a
      href={href}
      className="flex items-center gap-3 rounded-2xl border border-border bg-surface p-4 active:scale-[0.99] transition"
    >
      <span className="text-2xl">{emoji}</span>
      <span className="min-w-0">
        <span className="block font-semibold">{title}</span>
        <span className="block truncate text-xs text-muted">{desc}</span>
      </span>
      <span className="ml-auto text-muted">›</span>
    </a>
  );
}

function ApiStatus({ estado }: { estado: Estado }) {
  let dot = "bg-muted";
  let txt = "Conectando con el servidor…";
  if (estado.fase === "ok") {
    dot = "bg-brand";
    txt = estado.cerrado
      ? "Conectado · torneo CERRADO (puntajes finales)"
      : "Conectado · torneo abierto";
  } else if (estado.fase === "error") {
    dot = "bg-orange";
    txt = "Sin conexión con la API (¿uvicorn en :8000?)";
  }
  return (
    <div className="flex items-center gap-2 rounded-xl border border-border bg-surface-2 px-3 py-2 text-xs">
      <span className={`h-2 w-2 rounded-full ${dot}`} />
      <span className="text-muted">{txt}</span>
    </div>
  );
}
