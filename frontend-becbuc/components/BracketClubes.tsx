"use client";

import type { ClubRonda, ClubLlave, ClubLeg, Team } from "@/lib/types";
import PanZoom from "@/components/PanZoom";

/**
 * Bracket para torneos de CLUBES (Libertadores/Sudamericana).
 * - Dos lados convergentes hacia la Final (sin 3er puesto).
 * - Progresion SIEMPRE completa hasta la Final: rondas no cargadas = "Por definir".
 * - Cada llave = tarjeta con las dos piernas (ida/vuelta), cada una con su fecha
 *   corta (dd/mm HHhs), global y quien pasa.
 * - PanZoom: arrastre con dedo/mouse + zoom. Tocar una llave abre Pronosticos.
 */

const KO_ORDER = ["ronda32", "ronda16", "cuartos", "semis", "final"];
const NOMBRE: Record<string, string> = {
  ronda32: "16avos", ronda16: "Octavos", cuartos: "Cuartos", semis: "Semis", final: "Final",
};

const COLW = 200;
const GAP = 10;
const HEADER_H = 22;
const CARD_SLOT = 120;

type Col = { tipo: string; nombre: string; final?: boolean; llaves: (ClubLlave | null)[] };

function fechaCorta(iso?: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (isNaN(d.getTime())) return "";
  // Siempre hora de Paraguay (America/Asuncion), sin importar el dispositivo.
  const parts = new Intl.DateTimeFormat("es", {
    timeZone: "America/Asuncion",
    day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit", hour12: false,
  }).formatToParts(d);
  const g = (t: string) => parts.find((x) => x.type === t)?.value ?? "";
  return g("day") + "/" + g("month") + " " + g("hour") + ":" + g("minute") + "hs";
}

export default function BracketClubes({
  rondas,
  onSelect,
}: {
  rondas: ClubRonda[];
  onSelect?: (partidoId: number) => void;
}) {
  const byTipo = new Map(rondas.map((r) => [r.tipo, r]));
  const firstIdx = KO_ORDER.findIndex((t) => byTipo.has(t));
  if (firstIdx < 0) {
    return <p className="py-10 text-center text-sm text-muted">Todavia no hay playoff cargado.</p>;
  }

  const seq = KO_ORDER.slice(firstIdx);
  const firstCount = byTipo.get(KO_ORDER[firstIdx])!.llaves.length;

  // Tamano de cada ronda: real si esta cargada; si es placeholder se infiere.
  // De 16avos (ronda32) a Octavos (ronda16) NO se reduce: entran cabezas de serie
  // (equipos ya clasificados esperando rival). De Octavos en adelante, la mitad.
  let prev = firstCount;
  const rounds: Col[] = seq.map((tipo, i) => {
    const real = byTipo.get(tipo);
    let count: number;
    if (real) count = real.llaves.length;
    else if (i === 0) count = firstCount;
    else if (tipo === "ronda16") count = prev;
    else count = Math.max(1, Math.ceil(prev / 2));
    prev = count;
    const llaves: (ClubLlave | null)[] = real ? real.llaves : new Array(count).fill(null);
    return { tipo, nombre: real?.nombre ?? NOMBRE[tipo] ?? tipo, llaves };
  });

  const finalRound = rounds[rounds.length - 1];
  const feeders = rounds.slice(0, -1);

  const leftCols: Col[] = feeders.map((c) => ({
    ...c,
    llaves: c.llaves.slice(0, Math.ceil(c.llaves.length / 2)),
  }));
  const rightCols: Col[] = feeders.map((c) => ({
    ...c,
    llaves: c.llaves.slice(Math.ceil(c.llaves.length / 2)),
  }));

  const orderedCols: Col[] = [
    ...leftCols,
    { ...finalRound, nombre: "Final", final: true, llaves: [finalRound.llaves[0] ?? null] },
    ...[...rightCols].reverse(),
  ];

  const maxCards = Math.max(1, ...leftCols.map((c) => c.llaves.length));
  const bodyH = maxCards * CARD_SLOT;
  const contentH = HEADER_H + bodyH + 16;
  const nCols = orderedCols.length;
  const contentW = nCols * COLW + (nCols + 1) * GAP;
  const focusX = GAP + leftCols.length * (COLW + GAP) + COLW / 2;

  return (
    <div>
      <p className="mb-2 text-center text-[11px] text-muted">
        Arrastra para moverte - toca una llave para ver los pronosticos
      </p>
      <PanZoom contentW={contentW} contentH={contentH} focusX={focusX} height="76vh">
        <div className="flex items-start" style={{ width: contentW, height: contentH, gap: GAP, padding: GAP }}>
          {orderedCols.map((c, i) => (
            <Column key={i} col={c} bodyH={bodyH} onSelect={onSelect} />
          ))}
        </div>
      </PanZoom>
    </div>
  );
}

function Column({
  col,
  bodyH,
  onSelect,
}: {
  col: Col;
  bodyH: number;
  onSelect?: (partidoId: number) => void;
}) {
  return (
    <div className="flex shrink-0 flex-col" style={{ width: COLW }}>
      <div
        className={"mb-1 truncate text-center text-[10px] font-bold uppercase tracking-wide " + (col.final ? "text-brand" : "text-[#5a6690]")}
        style={{ height: HEADER_H }}
      >
        {col.final ? "Final" : col.nombre}
      </div>
      <div
        className={"flex flex-col " + (col.final ? "justify-center" : "justify-around")}
        style={{ height: bodyH }}
      >
        {col.llaves.map((ll, i) => (
          <LlaveCard key={i} ll={ll} onSelect={onSelect} />
        ))}
      </div>
    </div>
  );
}

function LlaveCard({
  ll,
  onSelect,
}: {
  ll: ClubLlave | null;
  onSelect?: (partidoId: number) => void;
}) {
  if (!ll) {
    return (
      <div className="my-1">
        <div className="flex h-[60px] items-center justify-center rounded-lg border border-dashed border-[#1e2850] text-[10px] italic text-[#2a2f45]">
          Por definir
        </div>
      </div>
    );
  }
  const enVivo = ll.estado === "en_juego";
  const fin = ll.estado === "finalizado";
  const border = enVivo ? "#ef4444" : fin ? "#1a2d1a" : "#1a2550";
  const winName = ll.ganador === "A" ? ll.teamA?.nombre : ll.ganador === "B" ? ll.teamB?.nombre : null;

  let footer: string | null = null;
  if (winName) {
    footer = "pasa " + short(winName);
    if (ll.globalA != null && ll.globalB != null) footer = "Global " + ll.globalA + "-" + ll.globalB + " - " + footer;
    if (ll.penales) footer = footer + " (pen " + ll.penales + ")";
  }

  const pid = ll.vuelta?.partido_id ?? ll.ida?.partido_id ?? null;
  const clickable = onSelect != null && pid != null;
  function handleClick() {
    if (onSelect != null && pid != null) onSelect(pid);
  }

  return (
    <div
      className="my-1"
      onClick={clickable ? handleClick : undefined}
      style={{ cursor: clickable ? "pointer" : "default" }}
    >
      <div
        style={{ background: "#0f1225", border: "1px solid " + border, borderRadius: 8 }}
        className="overflow-hidden"
      >
        <LegRow tag="I" leg={ll.ida} teamA={ll.teamA} teamB={ll.teamB} isIda={true} />
        <DateLine fecha={ll.ida?.fecha} />
        <div style={{ borderTop: "1px solid #080a12" }} />
        <LegRow tag="V" leg={ll.vuelta} teamA={ll.teamA} teamB={ll.teamB} isIda={false} />
        <DateLine fecha={ll.vuelta?.fecha} />
      </div>
      {footer ? (
        <div className="truncate border-x border-b border-[#1e2850] bg-[#0f1225] px-1.5 py-0.5 text-center text-[8.5px] text-[#6ee7b7]">
          {footer}
        </div>
      ) : null}
    </div>
  );
}

function DateLine({ fecha }: { fecha?: string | null }) {
  const t = fechaCorta(fecha);
  return <div className="px-1.5 pb-0.5 text-center text-[8px] text-[#7a86a8]">{t || "-"}</div>;
}

function LegRow({
  tag,
  leg,
  teamA,
  teamB,
  isIda,
}: {
  tag: string;
  leg: ClubLeg | null;
  teamA: Team | null;
  teamB: Team | null;
  isIda: boolean;
}) {
  const rawL = leg ? leg.local : null;
  const rawV = leg ? leg.visitante : null;
  const usar = (rawL === null || rawV === null) && teamA !== null && teamB !== null;
  const local = usar ? (isIda ? teamB : teamA) : rawL;
  const visit = usar ? (isIda ? teamA : teamB) : rawV;
  const gl = leg ? leg.gl : null;
  const gv = leg ? leg.gv : null;
  const played = leg != null && leg.estado === "finalizado" && gl != null && gv != null;
  const winL = played && (gl as number) > (gv as number);
  const winV = played && (gv as number) > (gl as number);
  const scoreTxt = (gl == null ? "-" : String(gl)) + ":" + (gv == null ? "-" : String(gv));
  return (
    <div className="flex h-[26px] items-center gap-1 px-1.5 pt-0.5 text-[10px]">
      <span className="w-2.5 shrink-0 text-[7px] font-bold text-[#4a5170]">{tag}</span>
      <Crest team={local} />
      <span className="flex-1 truncate" style={{ color: winL ? "#e8ecff" : "#8b93b4", fontWeight: winL ? 700 : 500 }}>
        {short(local?.nombre)}
      </span>
      <span className="shrink-0 font-bold text-[#cdd6f4]">{scoreTxt}</span>
      <span className="flex-1 truncate text-right" style={{ color: winV ? "#e8ecff" : "#8b93b4", fontWeight: winV ? 700 : 500 }}>
        {short(visit?.nombre)}
      </span>
      <Crest team={visit} />
    </div>
  );
}

function Crest({ team }: { team: Team | null }) {
  if (team?.logo_url) {
    // eslint-disable-next-line @next/next/no-img-element
    return <img src={team.logo_url} alt="" draggable={false} className="h-3.5 w-3.5 shrink-0 object-contain" />;
  }
  return <span className="w-3.5 shrink-0 text-center text-[7px] text-[#4a5170]">{team?.iso || "?"}</span>;
}

function short(name?: string | null): string {
  if (!name) return "?";
  return name.length > 10 ? name.slice(0, 9) + "." : name;
}
