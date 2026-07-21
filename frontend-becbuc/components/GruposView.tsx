"use client";

import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { type Group, type GroupMatch } from "@/lib/types";
import { fmtFecha } from "@/lib/format";

export default function GruposView({
  torneoId,
  onSelect,
}: {
  torneoId: number;
  onSelect: (num: number) => void;
}) {
  const [grupos, setGrupos] = useState<Group[] | null>(null);
  const [idx, setIdx] = useState(0); // siempre arranca en el Grupo A (índice 0)

  useEffect(() => {
    setGrupos(null);
    api
      .get<Group[]>(`/bets/grupos/${torneoId}`)
      .then((g) => setGrupos(Array.isArray(g) ? g : []))
      .catch(() => setGrupos([]));
    const t = setInterval(() => {
      api.get<Group[]>(`/bets/grupos/${torneoId}`).then((g) => Array.isArray(g) && setGrupos(g)).catch(() => {});
    }, 30000);
    return () => clearInterval(t);
  }, [torneoId]);

  const start = useRef<{ x: number; y: number } | null>(null);
  const go = (delta: number) => {
    if (!grupos) return;
    setIdx((i) => Math.max(0, Math.min(grupos.length - 1, i + delta)));
  };
  const onDown = (e: React.PointerEvent) => { start.current = { x: e.clientX, y: e.clientY }; };
  const onUp = (e: React.PointerEvent) => {
    if (!start.current) return;
    const dx = e.clientX - start.current.x, dy = e.clientY - start.current.y;
    start.current = null;
    if (Math.abs(dx) > 50 && Math.abs(dx) > Math.abs(dy)) go(dx < 0 ? 1 : -1);
  };

  if (grupos === null) return <p className="py-10 text-center text-sm text-muted">Cargando…</p>;
  if (grupos.length === 0) return <p className="py-10 text-center text-sm text-muted">Sin grupos.</p>;
  const g = grupos[Math.min(idx, grupos.length - 1)];

  return (
    <div
      className="flex flex-col gap-3 select-none"
      onPointerDown={onDown}
      onPointerUp={onUp}
      style={{ touchAction: "pan-y" }}
    >
      <div className="flex items-center justify-between gap-1">
        <div className="flex gap-1">
          <NavBtn dir="⏮" onClick={() => setIdx(0)} disabled={idx <= 0} />
          <NavBtn dir="‹" onClick={() => go(-1)} disabled={idx <= 0} />
        </div>
        <div className="text-center">
          <div className="text-sm font-bold text-brand">{g.fase_nombre}</div>
          <div className="text-[10px] text-muted">deslizá ↔ ({idx + 1}/{grupos.length})</div>
        </div>
        <div className="flex gap-1">
          <NavBtn dir="›" onClick={() => go(1)} disabled={idx >= grupos.length - 1} />
          <NavBtn dir="⏭" onClick={() => setIdx(grupos.length - 1)} disabled={idx >= grupos.length - 1} />
        </div>
      </div>

      {/* Tabla de posiciones */}
      <div className="overflow-hidden rounded-xl border border-border">
        <div className="grid grid-cols-[1.4rem_1fr_1.6rem_1.6rem_1.6rem_1.8rem] items-center gap-1 bg-surface-2 px-2 py-1 text-[10px] font-bold text-muted">
          <span>#</span><span>Equipo</span><span className="text-center">PJ</span>
          <span className="text-center">DG</span><span className="text-center">GF</span>
          <span className="text-center">Pts</span>
        </div>
        {g.standings.map((s, i) => (
          <div
            key={s.equipo_id}
            className={`grid grid-cols-[1.4rem_1fr_1.6rem_1.6rem_1.6rem_1.8rem] items-center gap-1 border-t border-border px-2 py-1.5 text-xs ${
              s.clasifica ? "bg-brand/10" : "bg-surface"
            }`}
          >
            <span className={`text-center font-bold ${s.clasifica ? "text-brand" : "text-muted"}`}>{i + 1}</span>
            <span className="flex min-w-0 items-center gap-1.5">
              {s.logo_url ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={s.logo_url} alt="" className="h-4 w-4 shrink-0 object-contain" />
              ) : null}
              <span className="truncate">{s.nombre}</span>
              {s.clasifica && <span className="text-[9px] text-brand">✓</span>}
            </span>
            <span className="text-center text-muted">{s.pj}</span>
            <span className="text-center text-muted">{s.gd > 0 ? `+${s.gd}` : s.gd}</span>
            <span className="text-center text-muted">{s.gf}</span>
            <span className="text-center font-bold text-brand">{s.pts}</span>
          </div>
        ))}
      </div>

      {/* Partidos del grupo */}
      <div className="px-1 text-[11px] font-semibold text-muted">Partidos</div>
      <div className="flex flex-col gap-2">
        {g.partidos
          .slice()
          .sort((a, b) => a.numero_fifa - b.numero_fifa)
          .map((m) => (
            <MatchRow key={m.id} m={m} onClick={() => onSelect(m.numero_fifa)} />
          ))}
      </div>
    </div>
  );
}

function MatchRow({ m, onClick }: { m: GroupMatch; onClick: () => void }) {
  const done = m.estado === "finalizado";
  const live = m.estado === "en_juego";
  const lname = m.local_nombre_es || m.local_nombre;
  const vname = m.visit_nombre_es || m.visit_nombre;
  return (
    <button
      onClick={onClick}
      className="flex items-center gap-2 rounded-xl border border-border bg-surface px-3 py-2 text-left text-xs active:bg-surface-2"
    >
      <span className="min-w-0 flex-1 truncate text-right">{lname}</span>
      <span className="shrink-0 rounded bg-surface-2 px-2 py-0.5 font-bold text-brand">
        {done || live ? `${m.goles_local ?? "-"}–${m.goles_visitante ?? "-"}` : "vs"}
      </span>
      <span className="min-w-0 flex-1 truncate">{vname}</span>
      <span className="ml-1 shrink-0 text-[10px] text-muted">
        {live ? "🔴" : done ? "✓" : m.fecha ? fmtFecha(m.fecha).split(",")[0] : ""}
      </span>
    </button>
  );
}

function NavBtn({ dir, onClick, disabled }: { dir: string; onClick: () => void; disabled: boolean }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className="grid h-9 w-9 place-items-center rounded-lg border border-border bg-surface text-lg leading-none disabled:opacity-30 active:bg-surface-2"
    >
      {dir}
    </button>
  );
}
