"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import {
  type Apostador,
  type MisPartidoRow,
} from "@/lib/types";
import { faseLabel, fmtFecha } from "@/lib/format";

const LS_KEY = "becbuc_apostador";

type ItemRow = {
  icon: string;
  label: string;
  real: string | number | null;
  pred: string | number | null;
  pts: number | null;
  done: boolean;
  section?: string;
};

export default function MiProno({
  torneoId,
  readOnly,
  focusNum,
}: {
  torneoId: number;
  readOnly: boolean;
  focusNum: number | null;
}) {
  const [apostadores, setApostadores] = useState<Apostador[] | null>(null);
  const [sel, setSel] = useState<number | null>(null);
  const [rows, setRows] = useState<MisPartidoRow[] | null>(null);
  const [loading, setLoading] = useState(false);
  // Editor
  const [edits, setEdits] = useState<Record<number, Record<string, number | null>>>({});
  const [pin, setPin] = useState("");
  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState<string | null>(null);
  const [filter, setFilter] = useState<"todos" | "pendientes">("todos");

  // Precargar el formulario con las predicciones actuales de cada partido.
  useEffect(() => {
    const e: Record<number, Record<string, number | null>> = {};
    for (const m of rows ?? []) {
      e[m.numero_fifa] = {
        pred_local: m.pred_local, pred_visitante: m.pred_visitante,
        pred_amarillas: m.pred_amarillas, pred_rojas: m.pred_rojas, pred_var: m.pred_var,
        pred_penales_partido: m.pred_penales_partido, pred_minuto_gol: m.pred_minuto_gol,
        pred_penales_local_tanda: m.pred_penales_local_tanda,
        pred_penales_visitante_tanda: m.pred_penales_visitante_tanda,
        pred_equipo_clasifica: m.pred_equipo_clasifica,
      };
    }
    setEdits(e);
    setSaveMsg(null);
  }, [rows]);

  // Cargar lista de apostadores + apostador guardado.
  useEffect(() => {
    api
      .get<Apostador[]>("/bets/apostadores")
      .then((a) => setApostadores(Array.isArray(a) ? a : []))
      .catch(() => setApostadores([]));
    const saved = typeof window !== "undefined" ? window.localStorage.getItem(LS_KEY) : null;
    if (saved) setSel(Number(saved));
  }, []);

  const loadRows = useCallback(async (uid: number) => {
    setLoading(true);
    try {
      const r = await api.get<MisPartidoRow[]>(
        `/bets/mis-partidos/${torneoId}?for_apostador_id=${uid}`
      );
      setRows(Array.isArray(r) ? r : []);
    } catch {
      setRows([]);
    } finally {
      setLoading(false);
    }
  }, [torneoId]);

  useEffect(() => {
    if (sel != null) loadRows(sel);
  }, [sel, loadRows]);

  // Al entrar desde el bracket, hacer scroll al partido tocado.
  useEffect(() => {
    if (focusNum == null) return;
    const el = document.getElementById(`mp-${focusNum}`);
    if (el) el.scrollIntoView({ behavior: "smooth", block: "center" });
  }, [focusNum, rows]);

  const pick = (uid: number) => {
    setSel(uid);
    if (typeof window !== "undefined") window.localStorage.setItem(LS_KEY, String(uid));
  };

  // Todos los partidos (grupos + KO). Clave de fase: en grupos cada grupo es su
  // propia fase (por fase_nombre); en KO la clave es fase_tipo.
  const all = rows ?? [];
  const phaseKey = (m: MisPartidoRow) =>
    (m.fase_tipo || "").startsWith("grupo") ? m.fase_nombre : m.fase_tipo;
  const byNum: Record<number, MisPartidoRow> = {};
  for (const m of all) byNum[m.numero_fifa] = m;

  // Fase abierta = la que tiene un partido en juego; si no, la más próxima programada.
  const enJuego = all.find((m) => m.estado === "en_juego");
  const prog = all
    .filter((m) => m.estado === "programado")
    .sort((a, b) => a.fase_orden - b.fase_orden)[0];
  const activeKey = enJuego ? phaseKey(enJuego) : prog ? phaseKey(prog) : null;

  // Fase a mostrar: la del partido tocado; sino la abierta; si TODO cerrado, la FINAL (P104).
  const closedKey = byNum[104] ? phaseKey(byNum[104]) : all.length ? phaseKey(all[all.length - 1]) : null;
  const focusKey =
    focusNum != null ? (byNum[focusNum] ? phaseKey(byNum[focusNum]) : null) : activeKey ?? closedKey;
  // Solo partidos con equipos DEFINIDOS (excluye placeholders "Por Definir", "TBD",
  // "Gan. X/Y" de los cruces aun no jugados). Se puede pronosticar solo esos.
  const _TBD = /^(por definir|tbd|gan\.)/i;
  const _def = (n?: string | null) => !!n && !_TBD.test(String(n).trim());
  const show = focusKey
    ? all
        .filter((m) => phaseKey(m) === focusKey && _def(m.local_nombre) && _def(m.visit_nombre))
        .sort((a, b) => a.numero_fifa - b.numero_fifa)
    : [];
  const first = show[0];
  const title = first
    ? `${(first.fase_tipo || "").startsWith("grupo") ? first.fase_nombre : faseLabel(first.fase_tipo)} · ${show.length} partido${show.length === 1 ? "" : "s"}`
    : "";

  const setEdit = (num: number, k: string, v: number | null) =>
    setEdits((e) => ({ ...e, [num]: { ...(e[num] || {}), [k]: v } }));

  async function guardar() {
    if (sel == null) return;
    const editables = show.filter((m) => m.estado === "programado");
    if (editables.length === 0) { setSaveMsg("No hay partidos abiertos para editar."); return; }
    const apuestas = editables.map((m) => {
      const e = edits[m.numero_fifa] || {};
      return {
        numero_fifa: m.numero_fifa,
        pred_local: e.pred_local ?? 0,
        pred_visitante: e.pred_visitante ?? 0,
        pred_amarillas: e.pred_amarillas ?? null,
        pred_rojas: e.pred_rojas ?? null,
        pred_var: e.pred_var ?? null,
        pred_penales_partido: e.pred_penales_partido ?? null,
        pred_minuto_gol: e.pred_minuto_gol ?? null,
        pred_penales_local_tanda: e.pred_penales_local_tanda ?? null,
        pred_penales_visitante_tanda: e.pred_penales_visitante_tanda ?? null,
        pred_equipo_clasifica: e.pred_equipo_clasifica ?? null,
      };
    });
    setSaving(true); setSaveMsg(null);
    try {
      const r = await api.post<{ ok: boolean; error?: string }>(
        `/bets/live-guardar-apuestas/${torneoId}`,
        { apostador_id: sel, pin, apuestas }
      );
      if (r?.ok) { setSaveMsg("\u2713 Guardado"); await loadRows(sel); }
      else setSaveMsg("\u2717 " + (r?.error || "No se pudo guardar"));
    } catch (err) {
      setSaveMsg("\u2717 " + String(err));
    } finally { setSaving(false); }
  }

  return (
    <div className="flex flex-col gap-3">
      <Selector apostadores={apostadores} sel={sel} onPick={pick} />

      {sel == null ? (
        <Msg text="Elegí tu nombre arriba para ver tu pronóstico." />
      ) : loading ? (
        <Msg text="Cargando…" />
      ) : show.length === 0 ? (
        <Msg text="No hay ninguna fase en juego. Tocá un partido en el Bracket." />
      ) : (
        <>
          <div className="px-1 text-xs font-semibold text-muted">{title}</div>
          {show.map((m, i) =>
            !readOnly && m.estado === "programado" ? (
              <EditableMatch
                key={m.numero_fifa ?? `e-${i}`}
                m={m}
                idx={i + 1}
                total={show.length}
                ed={edits[m.numero_fifa] || {}}
                onEdit={(k, v) => setEdit(m.numero_fifa, k, v)}
              />
            ) : (
              <MatchCotejo key={m.numero_fifa ?? `idx-${i}`} m={m} idx={i + 1} total={show.length} />
            )
          )}
          {!readOnly && show.some((m) => m.estado === "programado") ? (
            <SaveBar pin={pin} setPin={setPin} saving={saving} msg={saveMsg} onSave={guardar} />
          ) : null}
        </>
      )}
    </div>
  );
}

function Selector({
  apostadores,
  sel,
  onPick,
}: {
  apostadores: Apostador[] | null;
  sel: number | null;
  onPick: (uid: number) => void;
}) {
  return (
    <label className="flex items-center gap-2 rounded-xl border border-border bg-surface px-3 py-2">
      <span className="text-lg">👤</span>
      <select
        value={sel ?? ""}
        onChange={(e) => onPick(Number(e.target.value))}
        className="flex-1 bg-transparent text-sm outline-none"
      >
        <option value="" disabled>
          Elegí tu nombre…
        </option>
        {(apostadores ?? []).map((a) => (
          <option key={a.id} value={a.id} className="bg-surface">
            {a.alias || a.username}
          </option>
        ))}
      </select>
    </label>
  );
}

function NumInput({ value, onChange, w = "w-12" }: { value: number | null | undefined; onChange: (v: number | null) => void; w?: string }) {
  return (
    <input
      type="number"
      inputMode="numeric"
      value={value ?? ""}
      onChange={(e) => onChange(e.target.value === "" ? null : Number(e.target.value))}
      className={`${w} rounded border border-border bg-surface-2 px-1 py-0.5 text-center text-sm`}
    />
  );
}

const BONUS_ED: { k: string; icon: string; label: string }[] = [
  { k: "pred_amarillas", icon: "\u{1F7E8}", label: "Amar." },
  { k: "pred_rojas", icon: "\u{1F7E5}", label: "Rojas" },
  { k: "pred_var", icon: "\u{1F4FA}", label: "VAR" },
  { k: "pred_penales_partido", icon: "\u{1F945}", label: "Pen." },
  { k: "pred_minuto_gol", icon: "\u23F1", label: "Min" },
];

function EditableMatch({
  m, idx, total, ed, onEdit,
}: {
  m: MisPartidoRow; idx: number; total: number;
  ed: Record<string, number | null>; onEdit: (k: string, v: number | null) => void;
}) {
  return (
    <div id={`mp-${m.numero_fifa}`} className="scroll-mt-24 overflow-hidden rounded-xl border border-brand/40 bg-surface">
      <div className="bg-surface-2 px-3 py-1 text-center text-[11px] font-semibold text-brand">
        Editar pronostico · Partido {idx} de {total}
      </div>
      <div className="flex items-center justify-between gap-2 px-3 py-2">
        <span className="flex min-w-0 flex-1 items-center gap-1.5 text-sm font-semibold">
          {m.local_logo ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={m.local_logo} alt="" className="h-4 w-4 shrink-0 object-contain" />
          ) : null}
          <span className="truncate">{m.local_nombre}</span>
        </span>
        <div className="flex items-center gap-1">
          <NumInput value={ed.pred_local} onChange={(v) => onEdit("pred_local", v)} />
          <span className="text-muted">-</span>
          <NumInput value={ed.pred_visitante} onChange={(v) => onEdit("pred_visitante", v)} />
        </div>
        <span className="flex min-w-0 flex-1 items-center justify-end gap-1.5 text-sm font-semibold">
          <span className="truncate">{m.visit_nombre}</span>
          {m.visit_logo ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={m.visit_logo} alt="" className="h-4 w-4 shrink-0 object-contain" />
          ) : null}
        </span>
      </div>
      <div className="grid grid-cols-5 gap-1 border-t border-border px-2 py-2">
        {BONUS_ED.map((b) => (
          <label key={b.k} className="flex flex-col items-center gap-0.5 text-[10px] text-muted">
            <span>{b.icon} {b.label}</span>
            <NumInput value={ed[b.k]} onChange={(v) => onEdit(b.k, v)} w="w-full" />
          </label>
        ))}
      </div>
    </div>
  );
}

function SaveBar({ pin, setPin, saving, msg, onSave }: { pin: string; setPin: (v: string) => void; saving: boolean; msg: string | null; onSave: () => void }) {
  return (
    <div className="sticky bottom-0 flex flex-col gap-2 rounded-xl border border-border bg-surface p-3">
      <div className="flex items-center gap-2">
        <input
          value={pin}
          onChange={(e) => setPin(e.target.value)}
          placeholder="PIN (tu primer nombre)"
          className="flex-1 rounded-lg border border-border bg-surface-2 px-2 py-1.5 text-sm"
        />
        <button
          onClick={onSave}
          disabled={saving || !pin.trim()}
          className="rounded-lg bg-brand px-4 py-1.5 text-sm font-bold text-black disabled:opacity-40"
        >
          {saving ? "Guardando..." : "Guardar"}
        </button>
      </div>
      {msg ? (
        <div className={`text-center text-xs ${msg.startsWith("\u2713") ? "text-brand" : "text-orange"}`}>{msg}</div>
      ) : null}
    </div>
  );
}

function MatchCotejo({ m, idx, total }: { m: MisPartidoRow; idx: number; total: number }) {
  const done = m.estado === "finalizado";
  const live = m.estado === "en_juego";
  const items = buildItems(m);
  const real =
    done || live ? `${m.goles_local ?? "-"} – ${m.goles_visitante ?? "-"}` : "vs";

  let lastSection: string | undefined;

  return (
    <div
      id={`mp-${m.numero_fifa}`}
      className="scroll-mt-24 overflow-hidden rounded-xl border border-border bg-surface"
    >
      <div className="bg-surface-2 px-3 py-1 text-center text-[11px] font-semibold text-muted">
        Partido {idx} de {total}
      </div>
      <div className="flex items-center justify-between border-b border-border px-3 py-2">
        <span className="flex min-w-0 flex-1 items-center gap-1.5 text-sm font-semibold">
          {m.local_logo ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={m.local_logo} alt="" className="h-4 w-4 shrink-0 object-contain" />
          ) : null}
          <span className="truncate">{m.local_nombre}</span>
        </span>
        <span className="px-2 text-sm font-bold text-brand">{real}</span>
        <span className="flex min-w-0 flex-1 items-center justify-end gap-1.5 text-sm font-semibold">
          <span className="truncate">{m.visit_nombre}</span>
          {m.visit_logo ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={m.visit_logo} alt="" className="h-4 w-4 shrink-0 object-contain" />
          ) : null}
        </span>
      </div>
      <div className="flex items-center justify-between px-3 py-1 text-[11px] text-muted">
        <span>P{m.numero_fifa}</span>
        <span>
          {live ? "🔴 En vivo" : done ? "Final" : m.fecha ? fmtFecha(m.fecha) : "Programado"}
        </span>
        <span className="font-bold text-brand">{m.pts_total ?? 0} pts</span>
      </div>
      <div>
        {items.map((it, i) => {
          const header = it.section && it.section !== lastSection ? it.section : null;
          if (it.section) lastSection = it.section;
          return (
            <div key={i}>
              {header && (
                <div className="border-t border-border bg-surface-2 px-3 py-1 text-[11px] font-semibold text-orange">
                  {header}
                </div>
              )}
              <ItemLine it={it} />
            </div>
          );
        })}
      </div>
    </div>
  );
}

function ItemLine({ it }: { it: ItemRow }) {
  const hit = it.pts != null && it.pts > 0;
  const miss = it.done && (it.pts ?? 0) === 0;
  const color = hit ? "text-brand" : miss ? "text-orange" : "text-muted";
  const mark = hit ? "✅" : miss ? "❌" : "⏳";
  return (
    <div className="flex items-center gap-2 border-t border-border px-3 py-1.5 text-xs">
      <span className="w-5 text-center">{it.icon}</span>
      <span className="flex-1 truncate">{it.label}</span>
      <span className="text-muted">
        <span className="text-[10px]">tú</span> {fmt(it.pred)}
      </span>
      <span className="w-px self-stretch bg-border" />
      <span>
        <span className="text-[10px] text-muted">real</span> {fmt(it.real)}
      </span>
      <span className={`w-10 text-right font-bold ${color}`}>
        {mark} {it.pts ?? "–"}
      </span>
    </div>
  );
}

function fmt(v: string | number | null): string {
  return v === null || v === undefined ? "–" : String(v);
}

function buildItems(m: MisPartidoRow): ItemRow[] {
  const done = m.estado === "finalizado";
  const live = m.estado === "en_juego";
  const has = done || live;
  const gl = m.goles_local,
    gv = m.goles_visitante,
    pl = m.pred_local,
    pv = m.pred_visitante;
  const hasPred = pl != null || pv != null;
  const wdl = (a: number | null, b: number | null) =>
    a == null || b == null ? null : a > b ? "Local" : a < b ? "Visit." : "Empate";

  const MATCH_SECTION = "📋 Ítems del partido";
  const out: ItemRow[] = [
    { icon: "⚽", label: "Resultado", real: wdl(gl, gv), pred: wdl(pl, pv), pts: m.pts_resultado, done, section: MATCH_SECTION },
    {
      icon: "🎯",
      label: "Marcador exacto",
      real: gl != null ? `${gl}-${gv}` : null,
      pred: hasPred ? `${pl ?? "?"}-${pv ?? "?"}` : null,
      pts: m.pts_marcador,
      done,
      section: MATCH_SECTION,
    },
  ];
  const opt = (
    cond: boolean,
    icon: string,
    label: string,
    real: number | null,
    pred: number | null,
    pts: number | null
  ) => {
    if (cond)
      out.push({ icon, label, real: has ? real : null, pred, pts, done, section: MATCH_SECTION });
  };
  opt(m.pred_amarillas != null || m.amarillas != null, "🟨", "Amarillas", m.amarillas, m.pred_amarillas, m.pts_amarillas);
  opt(m.pred_rojas != null || m.rojas != null, "🟥", "Rojas", m.rojas, m.pred_rojas, m.pts_rojas);
  opt(m.pred_var != null || m.decisiones_var != null, "📺", "VAR", m.decisiones_var, m.pred_var, m.pts_var);
  opt(m.pred_penales_partido != null || m.penales_partido != null, "🥅", "Penales (juego)", m.penales_partido, m.pred_penales_partido, m.pts_penales_partido);
  opt(m.pred_minuto_gol != null || m.minuto_primer_gol != null, "⏱", "Minuto gol", m.minuto_primer_gol, m.pred_minuto_gol, m.pts_minuto);

  // En fase de grupos NO hay tanda de penales ni país que clasifica: se ocultan.
  const isGroup = (m.fase_tipo || "").startsWith("grupo");
  const PENAL_SECTION = "⚡ Definición por penales";
  const tandaReal = m.penales_local != null || m.penales_visitante != null;
  const tandaPred =
    m.pred_penales_local_tanda != null || m.pred_penales_visitante_tanda != null;
  const shootout = tandaReal || tandaPred;
  if (!isGroup && shootout) {
    out.push({
      icon: "⚡",
      label: "Tanda penales",
      real: tandaReal ? `${m.penales_local ?? "-"}-${m.penales_visitante ?? "-"}` : null,
      pred: tandaPred
        ? `${m.pred_penales_local_tanda ?? "-"}-${m.pred_penales_visitante_tanda ?? "-"}`
        : null,
      pts: m.pts_penales_tanda,
      done,
      section: PENAL_SECTION,
    });
  }

  // P — País que clasifica. En victoria en tiempo normal se infiere del marcador;
  // en definición por penales, es el ganador de la tanda.
  const teamName = (id: number | null) =>
    id == null
      ? null
      : id === m.local_id
      ? m.local_nombre
      : id === m.visit_id
      ? m.visit_nombre
      : `#${id}`;
  const realClasif = teamName(m.equipo_clasificado_id);
  let predClasifId = m.pred_equipo_clasifica;
  if (predClasifId == null && pl != null && pv != null && pl !== pv) {
    predClasifId = pl > pv ? m.local_id : m.visit_id;
  }
  const predClasif = teamName(predClasifId);
  if (!isGroup && (realClasif != null || predClasif != null)) {
    out.push({
      icon: "🏳️",
      label: "País que clasifica",
      real: realClasif,
      pred: predClasif,
      pts: m.pts_equipo,
      done,
      section: shootout ? PENAL_SECTION : undefined,
    });
  }
  return out;
}

function Msg({ text }: { text: string }) {
  return <p className="py-8 text-center text-sm text-muted">{text}</p>;
}
