"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { api } from "@/lib/api";
import { type LivePartido, type BracketMatch } from "@/lib/types";
import { fmtFecha } from "@/lib/format";
import {
  classifyEvents,
  Timeline,
  SectionLabel,
  PenalTimeline,
  type Ev,
} from "@/components/EnVivo";

/**
 * Popup "recuperar partido": reproduce la historia de un partido terminado
 * minuto a minuto, con el mismo detalle que el Live (stats + timeline). Al
 * cerrar vuelve al partido seleccionado (solo oculta el overlay).
 */
export default function MatchReplay({
  partidoId,
  onClose,
}: {
  partidoId: number;
  onClose: () => void;
}) {
  const [d, setD] = useState<LivePartido | null>(null);
  const [loading, setLoading] = useState(true);
  const [t, setT] = useState(0); // minuto actual de la reproducción
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(4); // minutos por segundo
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    let vivo = true;
    setLoading(true);
    api
      .get<{ partido: LivePartido | null }>(`/bets/partido-detalle/${partidoId}`)
      .then((r) => {
        if (!vivo) return;
        setD(r?.partido ?? null);
      })
      .catch(() => vivo && setD(null))
      .finally(() => vivo && setLoading(false));
    return () => {
      vivo = false;
    };
  }, [partidoId]);

  const evs: Ev[] = useMemo(() => (d ? classifyEvents(d.eventos_api ?? [], d) : []), [d]);
  const maxMin = useMemo(() => {
    const m = evs.reduce((mx, e) => Math.max(mx, e.el), 0);
    return Math.max(90, m);
  }, [evs]);

  // Al cargar, mostrar el partido COMPLETO (idéntico al Live).
  useEffect(() => {
    if (d) setT(maxMin);
  }, [d, maxMin]);

  // Reproducción minuto a minuto.
  useEffect(() => {
    if (timer.current) clearInterval(timer.current);
    if (!playing) return;
    timer.current = setInterval(() => {
      setT((x) => {
        if (x >= maxMin) {
          setPlaying(false);
          return maxMin;
        }
        return x + 1;
      });
    }, Math.max(60, 1000 / speed));
    return () => {
      if (timer.current) clearInterval(timer.current);
    };
  }, [playing, speed, maxMin]);

  const reproducir = () => {
    setT(0);
    setPlaying(true);
  };

  if (loading) return <Overlay onClose={onClose}><P>Cargando…</P></Overlay>;
  if (!d) return <Overlay onClose={onClose}><P>No se pudo cargar el partido.</P></Overlay>;

  const shown = evs.filter((e) => e.el <= t);
  const hasGoalEv = evs.some((e) => e.kind === "goal" && e.icon === "⚽");
  const golesL = hasGoalEv
    ? shown.filter((e) => e.kind === "goal" && e.icon === "⚽" && e.side === "L").length
    : (t >= maxMin ? d.goles_local ?? 0 : 0);
  const golesV = hasGoalEv
    ? shown.filter((e) => e.kind === "goal" && e.icon === "⚽" && e.side === "V").length
    : (t >= maxMin ? d.goles_visitante ?? 0 : 0);

  const amar = shown.filter((e) => e.kind === "yellow").length;
  const roja = shown.filter((e) => e.kind === "red").length;
  const cambiosEv = shown.filter((e) => e.kind === "subst").length;
  const cambios = cambiosEv || (t >= maxMin ? (d.sustituciones ?? 0) : 0);
  const primerGol = d.minuto_primer_gol != null && t >= d.minuto_primer_gol ? d.minuto_primer_gol : null;
  const penFull = t >= 120 || t >= maxMin;

  // cur sintético para PenalTimeline (usa nombres/ids/logos de los equipos).
  const cur = {
    num: d.numero_fifa,
    local: { id: 0, nombre: d.equipo_local, logo_url: d.logo_local, iso: d.bandera_local ?? "" },
    visitante: { id: -1, nombre: d.equipo_visitante, logo_url: d.logo_visitante, iso: d.bandera_visitante ?? "" },
  } as unknown as BracketMatch;

  return (
    <Overlay onClose={onClose}>
      <div className="mb-2 flex items-center justify-between">
        <div className="text-xs font-bold text-brand">🎬 Repetición del partido</div>
        <button
          onClick={onClose}
          className="grid h-7 w-7 place-items-center rounded-lg border border-border bg-surface text-muted active:bg-surface-2"
          aria-label="Cerrar"
        >
          ✕
        </button>
      </div>

      {/* Encabezado idéntico al Live */}
      <div className="rounded-xl border border-border bg-surface p-3">
        <div className="mb-1 text-center text-[10px] text-muted">{d.fase_nombre}</div>
        <div className="flex items-center justify-between">
          <TeamBig name={d.equipo_local} logo={d.logo_local} />
          <div className="px-2 text-center">
            <div className="text-2xl font-extrabold text-brand">{golesL} – {golesV}</div>
            {d.penales_tanda_local != null && penFull && (
              <div className="text-[10px] text-[#fbbf24]">
                pen {d.penales_tanda_local}–{d.penales_tanda_visitante}
              </div>
            )}
          </div>
          <TeamBig name={d.equipo_visitante} logo={d.logo_visitante} align="right" />
        </div>
        <div className="mt-1 text-center text-[11px] text-muted">
          {t >= maxMin ? "Finalizado" : `Minuto ${t}'`}
          {d.fecha ? ` · ${fmtFecha(d.fecha)}` : ""}
        </div>
      </div>

      {/* Controles de reproducción */}
      <div className="mt-2 rounded-xl border border-border bg-surface-2 p-2">
        <div className="flex items-center gap-2">
          <button onClick={reproducir} className="rounded-lg bg-brand px-3 py-1 text-xs font-bold text-black active:opacity-80">
            ▶ Reproducir
          </button>
          <button onClick={() => setPlaying((p) => !p)} className="rounded-lg border border-border bg-surface px-3 py-1 text-xs font-semibold active:bg-surface-2">
            {playing ? "⏸ Pausa" : "▶ Seguir"}
          </button>
          <button onClick={() => { setPlaying(false); setT(maxMin); }} className="rounded-lg border border-border bg-surface px-3 py-1 text-xs font-semibold text-muted active:bg-surface-2">
            ⏭ Final
          </button>
          <div className="ml-auto flex items-center gap-1 text-[11px] text-muted">
            <span>vel.</span>
            {[2, 4, 8].map((s) => (
              <button
                key={s}
                onClick={() => setSpeed(s)}
                className={`rounded px-1.5 py-0.5 font-semibold ${speed === s ? "bg-brand text-black" : "bg-surface text-muted"}`}
              >
                x{s}
              </button>
            ))}
          </div>
        </div>
        <input
          type="range"
          min={0}
          max={maxMin}
          value={t}
          onChange={(e) => { setPlaying(false); setT(Number(e.target.value)); }}
          className="mt-2 w-full accent-[color:var(--brand)]"
          aria-label="Minuto"
        />
        <div className="flex justify-between text-[10px] text-muted">
          <span>0&apos;</span>
          <span className="font-bold text-brand">{t}&apos;</span>
          <span>{maxMin}&apos;</span>
        </div>
      </div>

      {/* Stats progresivas (mismos ítems del Live: Cambios en vez de VAR) */}
      <SectionLabel text="📋 Ítems del partido" />
      <div className="grid grid-cols-5 gap-1">
        <StatCell icon="🟨" label="Amar." v={amar} />
        <StatCell icon="🟥" label="Rojas" v={roja} />
        <StatCell icon="🔄" label="Cambios" v={cambios} />
        <StatCell icon="🥅" label="Pen." v={t >= maxMin ? d.penales_partido ?? 0 : shown.filter((e) => e.detail.toLowerCase().includes("penalty")).length} />
        <StatCell icon="⏱" label="1er gol" v={primerGol ?? "–"} />
      </div>

      <SectionLabel text="⏱ Eventos" />
      <Timeline evs={shown.filter((e) => e.el < 120)} />
      {d.penales_tanda_local != null && penFull && <PenalTimeline cur={cur} d={d} evs={evs} />}
    </Overlay>
  );
}

function StatCell({ icon, label, v }: { icon: string; label: string; v: number | string }) {
  return (
    <div className="rounded-lg border border-border bg-surface px-1 py-1.5 text-center">
      <div className="text-sm">{icon}</div>
      <div className="text-sm font-bold">{v}</div>
      <div className="text-[9px] text-muted">{label}</div>
    </div>
  );
}

function TeamBig({ name, logo, align }: { name: string; logo?: string | null; align?: "right" }) {
  void align;
  return (
    <div className="flex min-w-0 flex-1 flex-col items-center gap-1">
      {logo ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={logo} alt="" className="h-8 w-8 object-contain" />
      ) : (
        <div className="grid h-8 w-8 place-items-center rounded bg-surface-2 text-[10px] text-muted">?</div>
      )}
      <span className="w-full truncate text-center text-xs font-semibold">{name}</span>
    </div>
  );
}

function Overlay({ children, onClose }: { children: React.ReactNode; onClose: () => void }) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/70 p-3 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="my-6 w-full max-w-md rounded-2xl border border-border bg-bg p-3 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {children}
      </div>
    </div>
  );
}

function P({ children }: { children: React.ReactNode }) {
  return <p className="py-10 text-center text-sm text-muted">{children}</p>;
}
