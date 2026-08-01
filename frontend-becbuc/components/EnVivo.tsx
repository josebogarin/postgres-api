"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import {
  type BracketMatch,
  type BracketResponse,
  type LivePanelResponse,
  type LivePartido,
  type LiveEvent,
} from "@/lib/types";
import { faseLabel, fmtFecha } from "@/lib/format";

export default function EnVivo({ torneoId }: { torneoId: number }) {
  const [matches, setMatches] = useState<BracketMatch[] | null>(null);
  const [idx, setIdx] = useState(0);
  const [detail, setDetail] = useState<LivePartido | null>(null);
  const initDone = useRef(false);

  // Lista de partidos de playoff (bracket) para navegar.
  useEffect(() => {
    api
      .get<BracketResponse>(`/bets/bracket-real/${torneoId}`)
      .then((b) => {
        const list = (b?.partidos ?? []).slice().sort((a, z) => a.num - z.num);
        setMatches(list);
      })
      .catch(() => setMatches([]));
  }, [torneoId]);

  // Índice inicial: en vivo > próximo programado > último.
  useEffect(() => {
    if (!matches || initDone.current || matches.length === 0) return;
    initDone.current = true;
    const live = matches.findIndex((m) => m.en_vivo);
    const prog = matches.findIndex((m) => !m.finalizado && !m.en_vivo);
    setIdx(live >= 0 ? live : prog >= 0 ? prog : matches.length - 1);
  }, [matches]);

  const cur = matches && matches.length ? matches[Math.min(idx, matches.length - 1)] : null;

  // Detalle (stats + timeline) del partido actual, con refresco si está en vivo.
  const loadDetail = useCallback(async (num: number) => {
    try {
      const d = await api.get<LivePanelResponse>(`/bets/live-panel/${torneoId}?numero_fifa=${num}`);
      setDetail(d?.partido ?? null);
    } catch {
      setDetail(null);
    }
  }, [torneoId]);

  useEffect(() => {
    if (!cur) return;
    setDetail(null);
    loadDetail(cur.num);
    const t = setInterval(() => loadDetail(cur.num), 30000);
    return () => clearInterval(t);
  }, [cur, loadDetail]);

  // Swipe horizontal para navegar.
  const start = useRef<{ x: number; y: number } | null>(null);
  const go = (delta: number) => {
    if (!matches) return;
    setIdx((i) => Math.max(0, Math.min(matches.length - 1, i + delta)));
  };
  const onDown = (e: React.PointerEvent) => {
    start.current = { x: e.clientX, y: e.clientY };
  };
  const onUp = (e: React.PointerEvent) => {
    if (!start.current) return;
    const dx = e.clientX - start.current.x;
    const dy = e.clientY - start.current.y;
    start.current = null;
    if (Math.abs(dx) > 50 && Math.abs(dx) > Math.abs(dy)) go(dx < 0 ? 1 : -1);
  };

  if (matches === null) return <Msg text="Cargando…" />;
  if (!cur) return <Msg text="No hay partidos de playoff." />;

  const nextProg = matches.find((m) => !m.finalizado && !m.en_vivo);
  const live = cur.en_vivo || detail?.estado === "en_juego";
  const evs = detail ? classifyEvents(detail.eventos_api ?? [], detail) : [];
  let banner = faseLabel(cur.tipo);
  if (cur.num === 104) banner = "🏆 PARTIDO FINAL";
  else if (cur.num === 103) banner = "🥉 TERCER PUESTO";
  else if (!cur.finalizado && !cur.en_vivo && nextProg && nextProg.num === cur.num)
    banner = "⏭ PRÓXIMO PARTIDO";

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
          <div className="text-xs font-bold text-brand">{banner}</div>
          <div className="text-[10px] text-muted">
            {faseLabel(cur.tipo)} · deslizá ↔ ({idx + 1}/{matches.length})
          </div>
        </div>
        <div className="flex gap-1">
          <NavBtn dir="›" onClick={() => go(1)} disabled={idx >= matches.length - 1} />
          <NavBtn dir="⏭" onClick={() => setIdx(matches.length - 1)} disabled={idx >= matches.length - 1} />
        </div>
      </div>

      <select
        value={Math.min(idx, matches.length - 1)}
        onChange={(e) => setIdx(Number(e.target.value))}
        className="w-full rounded-lg border border-border bg-surface px-2 py-1.5 text-xs"
        aria-label="Elegir partido"
      >
        {matches.map((m, i) => (
          <option key={i} value={i} className="bg-surface">
            {(m.en_vivo ? "\u{1F534} " : m.finalizado ? "\u2713 " : "") +
              (m.local?.nombre ?? "?") + " vs " + (m.visitante?.nombre ?? "?")}
          </option>
        ))}
      </select>

      <div className="rounded-xl border border-border bg-surface p-3">
        {live && (
          <div className="mb-2 inline-flex items-center gap-1 rounded-full bg-orange/20 px-2 py-0.5 text-[11px] font-bold text-orange">
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-orange" /> EN VIVO
            {detail?.minuto_actual != null && ` · ${detail.minuto_actual}'`}
          </div>
        )}
        <div className="flex items-center justify-between">
          <TeamBig name={cur.local?.nombre ?? "Por definir"} logo={cur.local?.logo_url} />
          <Score cur={cur} detail={detail} />
          <TeamBig name={cur.visitante?.nombre ?? "Por definir"} logo={cur.visitante?.logo_url} align="right" />
        </div>
        <div className="mt-1 text-center text-[11px] text-muted">
          {cur.finalizado
            ? "Finalizado"
            : cur.en_vivo
            ? "En juego"
            : cur.fecha
            ? `📅 ${fmtFecha(cur.fecha)}`
            : "Pendiente"}
        </div>
      </div>

      {(cur.finalizado || cur.en_vivo) && detail && (
        <>
          <SectionLabel text="📋 Ítems del partido" />
          <Stats d={detail} evs={evs} />
          <SectionLabel text="⏱ Eventos" />
          <Timeline evs={evs} />
          {detail.penales_tanda_local != null && (
            <PenalTimeline cur={cur} d={detail} evs={evs} />
          )}
        </>
      )}

      {cur.finalizado && nextProg && (
        <div className="rounded-xl border border-border bg-surface-2 px-3 py-2 text-xs">
          <span className="text-muted">⏭ Próximo: </span>
          <span className="font-semibold">
            P{nextProg.num} {nextProg.local?.nombre ?? "?"} vs {nextProg.visitante?.nombre ?? "?"}
          </span>
          {nextProg.fecha && <span className="text-muted"> · {fmtFecha(nextProg.fecha)}</span>}
        </div>
      )}
      {cur.finalizado && !nextProg && (
        <p className="text-center text-xs text-muted">No hay próximo partido (torneo cerrado).</p>
      )}
    </div>
  );
}

function Score({ cur, detail }: { cur: BracketMatch; detail: LivePartido | null }) {
  const show = cur.finalizado || cur.en_vivo;
  const gl = detail?.goles_local ?? cur.gl;
  const gv = detail?.goles_visitante ?? cur.gv;
  const pen =
    cur.pen_l != null && cur.pen_v != null ? (
      <div className="text-[10px] text-[#fbbf24]">pen {cur.pen_l}–{cur.pen_v}</div>
    ) : null;
  return (
    <div className="px-2 text-center">
      <div className="text-2xl font-extrabold text-brand">
        {show ? `${gl ?? "-"} – ${gv ?? "-"}` : "vs"}
      </div>
      {pen}
    </div>
  );
}

function TeamBig({ name, logo, align }: { name: string; logo?: string | null; align?: "right" }) {
  return (
    <div className={`flex min-w-0 flex-1 flex-col items-center gap-1`}>
      {logo ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={logo} alt="" className="h-8 w-8 object-contain" />
      ) : (
        <div className="grid h-8 w-8 place-items-center rounded bg-surface-2 text-[10px] text-muted">?</div>
      )}
      <span className={`w-full truncate text-center text-xs font-semibold`}>{name}</span>
    </div>
  );
}

export type Ev = {
  el: number;
  min: string;
  side: "L" | "V";
  kind: "goal" | "yellow" | "red" | "var" | "subst" | "other";
  icon: string;
  player: string;
  detail: string;
  inn?: string;
  out?: string;
};

function isBench(e: LiveEvent): boolean {
  const pn = (e.player?.name || "").trim().toLowerCase();
  return e.player?.id == null || pn.startsWith("banco:") || pn.startsWith("banco ");
}

export function classifyEvents(eventos: LiveEvent[], d: LivePartido): Ev[] {
  // Jugadores con 1ª amarilla (para detectar 2ª amarilla aunque llegue como roja aparte).
  const sideOf = (e: LiveEvent): "L" | "V" => {
    const tid = e.team?.id;
    if (tid != null && d.visita_api_team_id != null && tid === d.visita_api_team_id) return "V";
    if (tid != null && d.local_api_team_id != null && tid === d.local_api_team_id) return "L";
    if ((e.team?.name || "").toLowerCase() === (d.equipo_visitante || "").toLowerCase()) return "V";
    return "L";
  };
  const out: Ev[] = [];
  for (const e of eventos ?? []) {
    const t = (e.type || "").toLowerCase();
    if (!t) continue;
    if (t === "card" && isBench(e)) continue; // banco / cuerpo técnico: no cuenta
    const dd = (e.detail || "").toLowerCase();
    const el = e.time?.elapsed ?? 0;
    const min = `${el}${e.time?.extra ? `+${e.time.extra}` : ""}'`;
    const side = sideOf(e);
    const base = { el, min, side, player: e.player?.name || "", detail: e.detail || "" };
    // Regla del sistema: cada amarilla suma amarilla (incluida la 2ª); la roja se cuenta aparte.
    if (t === "card") {
      if (dd.includes("red")) out.push({ ...base, kind: "red", icon: "🟥" });
      else out.push({ ...base, kind: "yellow", icon: "🟨" });
    } else if (t === "goal") {
      out.push({ ...base, kind: "goal", icon: dd.includes("miss") || dd.includes("missed") ? "❌" : "⚽" });
    } else if (t === "var") {
      out.push({ ...base, kind: "var", icon: "📺" });
    } else if (t === "subst") {
      out.push({
        ...base,
        kind: "subst",
        icon: "🔁",
        player: "",
        inn: e.player?.name || undefined,
        out: e.assist?.name || undefined,
      });
    }
  }
  return out.sort((a, b) => a.el - b.el);
}

function Stats({ d, evs }: { d: LivePartido; evs: Ev[] }) {
  // Totales derivados de los eventos (coinciden con el timeline).
  const amar = evs.filter((e) => e.kind === "yellow").length;
  const roja = evs.filter((e) => e.kind === "red").length;
  // Cambios (sustituciones) reemplazan a VAR. Prioriza el total oficial del
  // partido (d.sustituciones); si no, cuenta los eventos de sustitución.
  const cambiosEv = evs.filter((e) => e.kind === "subst").length;
  const cambios = d.sustituciones ?? cambiosEv;
  const cells = [
    { icon: "🟨", label: "Amar.", v: amar },
    { icon: "🟥", label: "Rojas", v: roja },
    { icon: "🔄", label: "Cambios", v: cambios },
    { icon: "🥅", label: "Pen.", v: d.penales_partido ?? 0 },
    { icon: "⏱", label: "1er gol", v: d.minuto_primer_gol },
  ];
  return (
    <div className="grid grid-cols-5 gap-1">
      {cells.map((c) => (
        <div key={c.label} className="rounded-lg border border-border bg-surface px-1 py-1.5 text-center">
          <div className="text-sm">{c.icon}</div>
          <div className="text-sm font-bold">{c.v ?? "–"}</div>
          <div className="text-[9px] text-muted">{c.label}</div>
        </div>
      ))}
    </div>
  );
}

export function SectionLabel({ text, color }: { text: string; color?: boolean }) {
  return (
    <div className={`px-1 pt-1 text-[11px] font-semibold ${color ? "text-orange" : "text-muted"}`}>
      {text}
    </div>
  );
}

// Detecta un penal de la TANDA (post-120', goal/miss). Se separa del timeline normal.
function isShootout(e: Ev): boolean {
  const dd = e.detail.toLowerCase();
  return e.el >= 120 && (e.kind === "goal" || dd.includes("penalty") || dd.includes("miss"));
}

export function Timeline({ evs }: { evs: Ev[] }) {
  const main = evs.filter((e) => !isShootout(e));
  if (main.length === 0)
    return <p className="text-center text-[11px] text-muted">Sin eventos registrados.</p>;
  return (
    <div className="flex flex-col gap-1">
      {main.map((r, i) => (
        <div key={i} className="grid grid-cols-[1fr_auto_1fr] items-center gap-2 text-xs">
          <div className="flex min-w-0 items-center justify-end gap-1 text-right">
            {r.side === "L" && <EvContent r={r} />}
          </div>
          <div className="rounded bg-surface-2 px-1.5 py-0.5 text-[10px] font-bold text-muted">
            {r.min}
          </div>
          <div className="flex min-w-0 items-center gap-1">
            {r.side === "V" && <EvContent r={r} />}
          </div>
        </div>
      ))}
    </div>
  );
}

function EvContent({ r }: { r: Ev }) {
  if (r.kind === "subst") {
    return (
      <span className="flex min-w-0 flex-wrap items-center gap-1">
        {r.inn && <span className="truncate rounded bg-brand/25 px-1 text-brand">▲ {r.inn}</span>}
        {r.out && <span className="truncate rounded bg-orange/25 px-1 text-orange">▼ {r.out}</span>}
      </span>
    );
  }
  return (
    <>
      <span className="min-w-0 truncate">{r.player}</span>
      <span>{r.icon}</span>
    </>
  );
}

export function PenalTimeline({ cur, d, evs }: { cur: BracketMatch; d: LivePartido; evs: Ev[] }) {
  const shots = evs.filter(isShootout);
  const conv = (e: Ev) => !(e.detail.toLowerCase().includes("miss") || e.icon === "❌");
  const cid = d.equipo_clasificado_id;
  const clasif =
    cid == null
      ? null
      : cid === cur.local?.id
      ? cur.local?.nombre
      : cid === cur.visitante?.id
      ? cur.visitante?.nombre
      : null;
  return (
    <div className="flex flex-col gap-2">
      <SectionLabel text="⚡ Definición por penales" color />
      {shots.length > 0 && (
        <div className="flex flex-col gap-1">
          {shots.map((r, i) => (
            <div key={i} className="grid grid-cols-[1fr_auto_1fr] items-center gap-2 text-xs">
              <div className="flex min-w-0 items-center justify-end gap-1 text-right">
                {r.side === "L" && (
                  <>
                    <span className="min-w-0 truncate">{r.player}</span>
                    <span>{conv(r) ? "✅" : "❌"}</span>
                  </>
                )}
              </div>
              <div className="text-[11px]">🥅</div>
              <div className="flex min-w-0 items-center gap-1">
                {r.side === "V" && (
                  <>
                    <span>{conv(r) ? "✅" : "❌"}</span>
                    <span className="min-w-0 truncate">{r.player}</span>
                  </>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
      <div className="rounded-xl border border-border bg-surface px-3 py-2 text-xs">
        <div className="flex items-center justify-between">
          <span className="text-muted">Resultado tanda</span>
          <span className="font-bold text-brand">
            {cur.local?.nombre} {d.penales_tanda_local ?? "-"} – {d.penales_tanda_visitante ?? "-"}{" "}
            {cur.visitante?.nombre}
          </span>
        </div>
        {clasif && (
          <div className="mt-1 flex items-center justify-between">
            <span className="text-muted">🏳️ Clasifica</span>
            <span className="font-semibold text-brand">{clasif}</span>
          </div>
        )}
      </div>
    </div>
  );
}

function NavBtn({ dir, onClick, disabled }: { dir: string; onClick: () => void; disabled: boolean }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className="grid h-9 w-9 place-items-center rounded-lg border border-border bg-surface text-xl leading-none disabled:opacity-30 active:bg-surface-2"
    >
      {dir}
    </button>
  );
}

function Msg({ text }: { text: string }) {
  return <p className="py-10 text-center text-sm text-muted">{text}</p>;
}
