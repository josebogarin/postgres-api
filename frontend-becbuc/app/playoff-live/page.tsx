"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import {
  TORNEO_ID,
  type BracketMatch,
  type BracketResponse,
  type RankingRow,
} from "@/lib/types";
import { ITEMS, alias } from "@/lib/format";
import BracketTree from "@/components/BracketTree";
import MiProno from "@/components/MiProno";
import EnVivo from "@/components/EnVivo";

type Tab = "bracket" | "envivo" | "ranking" | "miprono";

export default function PlayoffLive() {
  const [tab, setTab] = useState<Tab>("bracket");
  const [bracket, setBracket] = useState<BracketMatch[] | null>(null);
  const [ranking, setRanking] = useState<RankingRow[] | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [sel, setSel] = useState<number | null>(null);

  const selectMatch = (num: number) => {
    setSel(num);
    setTab("miprono");
  };

  const load = useCallback(async () => {
    try {
      const [b, r] = await Promise.all([
        api.get<BracketResponse>(`/bets/bracket-real/${TORNEO_ID}`),
        api.get<RankingRow[]>(`/bets/ranking/${TORNEO_ID}`),
      ]);
      setBracket(b?.partidos ?? []);
      setRanking(Array.isArray(r) ? r : []);
      setErr(null);
    } catch (e) {
      setErr(String(e));
    }
  }, []);

  useEffect(() => {
    load();
    const t = setInterval(load, 30000);
    return () => clearInterval(t);
  }, [load]);

  return (
    <main className="mx-auto w-full max-w-md pb-10">
      <TopBar />
      <TabBar tab={tab} setTab={setTab} />

      {err && (
        <p className="mx-4 mt-3 rounded-lg bg-surface-2 px-3 py-2 text-xs text-orange">
          Sin conexión con la API. Reintentando…
        </p>
      )}

      <div className="px-3 pt-3">
        {tab === "bracket" && (
          <BracketView partidos={bracket} onSelect={selectMatch} />
        )}
        {tab === "envivo" && <EnVivo />}
        {tab === "ranking" && <RankingView rows={ranking} />}
        {tab === "miprono" && <MiProno focusNum={sel} />}
      </div>
    </main>
  );
}

function TopBar() {
  return (
    <header className="sticky top-0 z-10 flex items-center gap-2 border-b border-border bg-bg/95 px-4 py-3 backdrop-blur">
      <a href="/" className="text-muted">
        ‹
      </a>
      <span className="text-2xl">🏆</span>
      <h1 className="font-bold">Playoff Live</h1>
    </header>
  );
}

function TabBar({ tab, setTab }: { tab: Tab; setTab: (t: Tab) => void }) {
  const tabs: { id: Tab; label: string }[] = [
    { id: "bracket", label: "Playoff" },
    { id: "envivo", label: "En Vivo" },
    { id: "miprono", label: "Pronósticos" },
    { id: "ranking", label: "Puntaje" },
  ];
  return (
    <div className="flex gap-1 border-b border-border px-3 pt-2">
      {tabs.map((t) => (
        <button
          key={t.id}
          onClick={() => setTab(t.id)}
          className={`flex-1 rounded-t-lg px-1.5 py-2 text-xs font-semibold transition ${
            tab === t.id ? "bg-surface text-brand" : "text-muted active:bg-surface/60"
          }`}
        >
          {t.label}
        </button>
      ))}
    </div>
  );
}

/* ---------------- Bracket ---------------- */

function BracketView({
  partidos,
  onSelect,
}: {
  partidos: BracketMatch[] | null;
  onSelect: (num: number) => void;
}) {
  if (partidos === null) return <Loading />;
  if (partidos.length === 0)
    return <Empty msg="Todavía no hay partidos de playoff." />;
  return <BracketTree partidos={partidos} onSelectMatch={onSelect} />;
}

/* ---------------- Ranking ---------------- */

function RankingView({ rows }: { rows: RankingRow[] | null }) {
  const [open, setOpen] = useState<number | null>(null);
  if (rows === null) return <Loading />;
  if (rows.length === 0) return <Empty msg="Ranking vacío." />;

  return (
    <div className="overflow-hidden rounded-xl border border-border">
      {rows.map((r, i) => {
        const isOpen = open === r.apostador_id;
        return (
          <div key={r.apostador_id} className="border-b border-border last:border-0">
            <button
              onClick={() => setOpen(isOpen ? null : r.apostador_id)}
              className="flex w-full items-center gap-3 bg-surface px-3 py-2.5 text-left active:bg-surface-2"
            >
              <span className="w-6 text-center text-sm font-bold text-muted">{i + 1}</span>
              <span className="min-w-0 flex-1 truncate text-sm font-medium">
                {alias(r)}
                {r.online_source && (
                  <span className="ml-1 text-[10px]">
                    {r.online_source === "movil" ? "📱" : "💻"}
                  </span>
                )}
              </span>
              <span className="text-sm font-bold text-brand">{r.puntos_total}</span>
              <span className="text-muted">{isOpen ? "▾" : "›"}</span>
            </button>
            {isOpen && <RankBreakdown r={r} />}
          </div>
        );
      })}
    </div>
  );
}

const FASE_RANK: Record<string, number> = {
  grupo: 0, ronda32: 1, ronda16: 2, cuartos: 3, semis: 4, tercer_puesto: 5, tercero: 5, final: 6,
};
const FASE_NOMBRE: Record<string, string> = {
  grupo: "Grupos", ronda32: "16avos", ronda16: "Octavos", cuartos: "Cuartos",
  semis: "Semifinal", tercer_puesto: "3er puesto", tercero: "3er puesto", final: "Final",
};

function RankBreakdown({ r }: { r: RankingRow }) {
  const [mode, setMode] = useState<"items" | "fase">("items");
  // Agregar por categoría de fase (los 12 grupos se combinan en "Grupos").
  const agg = new Map<string, number>();
  for (const f of r.fases ?? []) {
    const cat = (f.tipo || "").startsWith("grupo") ? "grupo" : f.tipo;
    agg.set(cat, (agg.get(cat) ?? 0) + (f.pts ?? 0));
  }
  const faseList = [...agg.entries()]
    .filter(([, pts]) => pts !== 0)
    .sort((a, b) => (FASE_RANK[a[0]] ?? 9) - (FASE_RANK[b[0]] ?? 9));

  return (
    <div className="bg-surface-2 px-3 py-2.5 text-xs">
      <div className="mb-2 flex gap-1">
        {(["items", "fase"] as const).map((mo) => (
          <button
            key={mo}
            onClick={() => setMode(mo)}
            className={`rounded-full px-2.5 py-0.5 font-semibold ${
              mode === mo ? "bg-brand text-black" : "bg-bg text-muted"
            }`}
          >
            {mo === "items" ? "Por ítem" : "Por fase"}
          </button>
        ))}
      </div>

      <div className="mb-2 flex flex-wrap gap-1">
        {mode === "items" ? (
          ITEMS.map(({ key, icon, label }) => {
            const v = (r[key] as number | undefined) ?? 0;
            return (
              <span
                key={label}
                className={`rounded px-1.5 py-0.5 ${
                  v > 0 ? "bg-brand/20 text-brand" : "bg-bg text-muted"
                }`}
              >
                {icon} {label}: {v}
              </span>
            );
          })
        ) : faseList.length === 0 ? (
          <span className="text-muted">—</span>
        ) : (
          faseList.map(([cat, pts]) => (
            <span key={cat} className="rounded bg-brand/20 px-1.5 py-0.5 text-brand">
              {FASE_NOMBRE[cat] ?? cat}: {pts}
            </span>
          ))
        )}
        <span className="rounded bg-orange/20 px-1.5 py-0.5 text-orange">
          🌐 Globales: {r.pts_globales ?? 0}
        </span>
      </div>

      <div className="flex gap-3 text-muted">
        <span>🟢 {r.plenos ?? 0} plenos</span>
        <span>🟡 {r.aciertos ?? 0} aciertos</span>
        <span>Part {r.puntos_partidos_total ?? 0}</span>
      </div>
    </div>
  );
}

/* ---------------- misc ---------------- */

function Loading() {
  return <p className="py-10 text-center text-sm text-muted">Cargando…</p>;
}
function Empty({ msg }: { msg: string }) {
  return <p className="py-10 text-center text-sm text-muted">{msg}</p>;
}
