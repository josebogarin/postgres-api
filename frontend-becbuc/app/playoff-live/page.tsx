"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import {
  type BracketMatch,
  type BracketResponse,
  type BracketClubesResponse,
  type ClubRonda,
  type RankingRow,
} from "@/lib/types";
import { ITEMS, alias } from "@/lib/format";
import BracketTree from "@/components/BracketTree";
import BracketClubes from "@/components/BracketClubes";
import MiProno from "@/components/MiProno";
import EnVivo from "@/components/EnVivo";
import GruposView from "@/components/GruposView";

type Tab = "bracket" | "grupos" | "envivo" | "ranking" | "miprono";

export default function PlayoffLive() {
  const router = useRouter();
  const [torneoId, setTorneoId] = useState<number | null>(null);
  const [torneoNombre, setTorneoNombre] = useState<string>("");
  const [readOnly, setReadOnly] = useState<boolean>(false);
  const [tab, setTab] = useState<Tab>("bracket");
  const [bracket, setBracket] = useState<BracketMatch[] | null>(null);
  const [bracketClubes, setBracketClubes] = useState<ClubRonda[] | null>(null);
  const [esClubes, setEsClubes] = useState(false);
  const [ranking, setRanking] = useState<RankingRow[] | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [sel, setSel] = useState<number | null>(null);

  // El torneo se elige en el login (root). Si no hay, volver a elegir.
  useEffect(() => {
    const id = Number(localStorage.getItem("becbuc_torneo"));
    if (!id) {
      router.replace("/");
      return;
    }
    setTorneoId(id);
    setTorneoNombre(localStorage.getItem("becbuc_torneo_nombre") || "BECBUC Live");
    setReadOnly(localStorage.getItem("becbuc_torneo_ro") === "1");
    setEsClubes(localStorage.getItem("becbuc_torneo_tercero") === "0");
  }, [router]);

  const salir = () => {
    localStorage.removeItem("becbuc_torneo");
    localStorage.removeItem("becbuc_torneo_nombre");
    localStorage.removeItem("becbuc_torneo_ro");
    router.replace("/");
  };

  const selectMatch = (num: number) => {
    setSel(num);
    setTab("miprono");
  };

  const load = useCallback(async () => {
    if (!torneoId) return;
    try {
      const r = await api.get<RankingRow[]>(`/bets/ranking/${torneoId}`);
      setRanking(Array.isArray(r) ? r : []);
      if (esClubes) {
        const bc = await api.get<BracketClubesResponse>(`/bets/bracket-clubes/${torneoId}`);
        setBracketClubes(bc?.rondas ?? []);
      } else {
        const b = await api.get<BracketResponse>(`/bets/bracket-real/${torneoId}`);
        setBracket(b?.partidos ?? []);
      }
      setErr(null);
    } catch (e) {
      setErr(String(e));
    }
  }, [torneoId, esClubes]);

  useEffect(() => {
    if (!torneoId) return;
    load();
    const t = setInterval(load, 30000);
    return () => clearInterval(t);
  }, [load, torneoId]);

  if (!torneoId) return null; // redirigiendo al login

  return (
    <main className="mx-auto w-full max-w-md md:max-w-3xl lg:max-w-none lg:px-6 pb-10">
      <TopBar nombre={torneoNombre} readOnly={readOnly} onExit={salir} />
      <TabBar tab={tab} setTab={setTab} />

      {err && (
        <p className="mx-4 mt-3 rounded-lg bg-surface-2 px-3 py-2 text-xs text-orange">
          Sin conexión con la API. Reintentando…
        </p>
      )}

      <div className="px-3 pt-3">
        {tab === "bracket" &&
          (esClubes ? (
            <ClubesView rondas={bracketClubes} onGoPronos={() => setTab("miprono")} />
          ) : (
            <BracketView partidos={bracket} onSelect={selectMatch} />
          ))}
        {tab === "grupos" && <GruposView torneoId={torneoId} onSelect={selectMatch} />}
        {tab === "envivo" && <EnVivo torneoId={torneoId} />}
        {tab === "ranking" && <RankingView rows={ranking} />}
        {tab === "miprono" && (
          <MiProno torneoId={torneoId} readOnly={readOnly} focusNum={sel} />
        )}
      </div>
    </main>
  );
}

function TopBar({
  nombre,
  readOnly,
  onExit,
}: {
  nombre: string;
  readOnly: boolean;
  onExit: () => void;
}) {
  return (
    <header className="sticky top-0 z-10 flex items-center gap-2 border-b border-border bg-bg/95 px-3 py-2.5 backdrop-blur">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src="/static/becbuc-logo.jpeg"
        alt="BECBUC"
        className="h-8 w-8 rounded-lg object-contain"
      />
      <div className="min-w-0 flex-1">
        <h1 className="truncate text-sm font-bold leading-tight">{nombre}</h1>
        {readOnly && (
          <span className="text-[10px] text-orange">Finalizado · solo lectura</span>
        )}
      </div>
      <button
        onClick={onExit}
        className="shrink-0 rounded-lg border border-border bg-surface px-2.5 py-1 text-xs font-semibold text-muted active:bg-surface-2"
      >
        Salir
      </button>
    </header>
  );
}

function TabBar({ tab, setTab }: { tab: Tab; setTab: (t: Tab) => void }) {
  const tabs: { id: Tab; icon: string; label: string }[] = [
    { id: "bracket", icon: "🏆", label: "Playoff" },
    { id: "grupos", icon: "⚽", label: "Grupos" },
    { id: "envivo", icon: "🔴", label: "En Vivo" },
    { id: "miprono", icon: "🎯", label: "Pronós." },
    { id: "ranking", icon: "🏅", label: "Puntaje" },
  ];
  return (
    <div className="flex gap-1 border-b border-border px-2 pt-2">
      {tabs.map((t) => (
        <button
          key={t.id}
          onClick={() => setTab(t.id)}
          className={`flex flex-1 flex-col items-center gap-0.5 rounded-t-lg px-1 py-1.5 transition ${
            tab === t.id ? "bg-surface text-brand" : "text-muted active:bg-surface/60"
          }`}
        >
          <span className="text-base leading-none">{t.icon}</span>
          <span className="text-[9px] font-semibold">{t.label}</span>
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

function ClubesView({
  rondas,
  onGoPronos,
}: {
  rondas: ClubRonda[] | null;
  onGoPronos: () => void;
}) {
  if (rondas === null) return <Loading />;
  if (rondas.length === 0) return <Empty msg="Todavía no hay partidos de playoff." />;
  return <BracketClubes rondas={rondas} onSelect={() => onGoPronos()} />;
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
